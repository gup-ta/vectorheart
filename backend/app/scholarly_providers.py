"""Allowlisted scholarly HTTP adapters. No arbitrary URL fetch, crawling or model citations."""
import hashlib
import html
import ipaddress
import json
import os
import re
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Protocol
from urllib.parse import quote, unquote, urlsplit
import httpx
from sqlalchemy import select, delete
from app.db import Session, now
from app.literature_models import LiteratureCache
from app.literature_schemas import Paper

HTTP_TRANSPORT = None  # Test injection only; never user-configured.
BASES = {'OpenAlex': 'https://api.openalex.org', 'Europe PMC': 'https://www.ebi.ac.uk/europepmc/webservices/rest', 'Crossref': 'https://api.crossref.org'}
_lock = threading.Lock()
_last = {}
_cooldown = {}


class ScholarlyError(Exception):
    def __init__(self, provider, code, message):
        self.provider, self.code, self.message = provider, code, message
        super().__init__(message)


class TextParser(HTMLParser):
    def __init__(self): super().__init__(convert_charrefs=True); self.parts = []
    def handle_data(self, data): self.parts.append(data)


def text(value, limit=16000):
    parser = TextParser(); parser.feed(str(value or '')[:100000])
    return re.sub(r'\s+', ' ', ' '.join(parser.parts)).strip()[:limit]


def doi(value):
    value = unquote(str(value or '')).strip()
    if value.lower().startswith('https://doi.org/'): value = value[16:]
    elif value.lower().startswith('http://doi.org/'): value = value[15:]
    elif value.lower().startswith('doi:'): value = value[4:].strip()
    value = value.lower()
    if not re.fullmatch(r'10\.\d{4,9}/[^\s?#<>"\\]{1,210}', value): raise ValueError('Enter a valid DOI, PMID, PMCID or OpenAlex work ID; arbitrary URLs are not fetched.')
    return value


def identifier(value):
    value = value.strip()
    if re.fullmatch(r'(?:https://openalex.org/)?W\d{1,16}', value, re.I): return 'openalex', value.rsplit('/', 1)[-1].upper()
    if re.fullmatch(r'(?:PMCID:)?PMC\d{1,12}', value, re.I): return 'pmcid', value.split(':')[-1].upper()
    if re.fullmatch(r'(?:PMID:)?\d{1,12}', value, re.I): return 'pmid', value.split(':')[-1]
    return 'doi', doi(value)


def safe_link(value):
    try:
        parsed = urlsplit(str(value or ''))
        if parsed.scheme not in ['https', 'http'] or not parsed.hostname or parsed.username or parsed.password or parsed.port not in [None, 80, 443]: return None
        host = parsed.hostname.lower()
        if host in ['localhost', 'metadata.google.internal'] or host.endswith(('.local', '.internal')): return None
        try:
            if not ipaddress.ip_address(host).is_global: return None
        except ValueError: pass
        if any(ord(c) < 32 for c in value): return None
        return value[:2000]
    except (ValueError, TypeError): return None


@dataclass
class RequestBudget:
    maximum: int = 8
    seconds: float = 45
    used: int = 0
    cache_hits: int = 0
    started: float = field(default_factory=time.monotonic)

    def remaining(self): return self.seconds - (time.monotonic() - self.started)
    def consume(self):
        if self.used >= self.maximum or self.remaining() <= 0: raise ScholarlyError('retrieval', 'budget', 'Scholarly request budget reached; preserved results remain available.')
        self.used += 1


def request_json(provider, path, params, budget):
    if provider not in BASES or not path.startswith('/') or '..' in path or '?' in path or '#' in path:
        raise ScholarlyError(provider, 'unsafe_request', 'Only registered scholarly API routes are allowed.')
    public_params = {k: v for k, v in params.items() if k != 'api_key'}
    cache_key = hashlib.sha256(json.dumps([provider, path, public_params], sort_keys=True).encode()).hexdigest()
    with Session() as s:
        cached = s.get(LiteratureCache, cache_key)
        if cached and datetime.fromisoformat(cached.expires_at) > datetime.now(timezone.utc):
            budget.cache_hits += 1; return cached.payload
    for attempt in range(2):
        with _lock:
            delay = max(_cooldown.get(provider, 0) - time.monotonic(), .5 - (time.monotonic() - _last.get(provider, 0)))
            if delay > 3 or delay >= budget.remaining(): raise ScholarlyError(provider, 'rate_limit', f'{provider} is cooling down after a rate limit. Retry later; cached records remain available.')
            if delay > 0: time.sleep(delay)
            _last[provider] = time.monotonic()
        budget.consume()
        private_params = dict(public_params)
        if provider == 'OpenAlex' and os.getenv('OPENALEX_API_KEY'): private_params['api_key'] = os.environ['OPENALEX_API_KEY']
        contact = os.getenv('LITERATURE_CONTACT_EMAIL', '').strip()
        if contact and provider == 'Crossref': private_params['mailto'] = contact
        try:
            headers = {'Accept': 'application/json', 'User-Agent': 'VectorHeart/0.1 scholarly research' + (f' (mailto:{contact})' if contact else '')}
            with httpx.Client(transport=HTTP_TRANSPORT, timeout=max(.1, min(10, budget.remaining())), follow_redirects=False, headers=headers) as client:
                with client.stream('GET', BASES[provider] + path, params=private_params) as response:
                    status = response.status_code
                    if status in [429, 503]:
                        retry = response.headers.get('retry-after', '2')
                        try: wait = float(retry)
                        except ValueError:
                            try: wait = (parsedate_to_datetime(retry) - datetime.now(timezone.utc)).total_seconds()
                            except (ValueError, TypeError): wait = 2
                        wait = max(1, min(3600, wait))
                        with _lock: _cooldown[provider] = time.monotonic() + wait
                        if attempt == 0 and wait <= 3 and budget.remaining() > wait: time.sleep(wait); continue
                        raise ScholarlyError(provider, 'rate_limit' if status == 429 else 'unavailable', f'{provider} returned HTTP {status}; retry after its cooldown. Existing results were preserved.')
                    if status == 404: raise ScholarlyError(provider, 'not_found', f'{provider} could not verify this identifier. No source was invented.')
                    if status in [401, 403]: raise ScholarlyError(provider, 'permissions', f'{provider} rejected API access; check its optional server credentials or access budget.')
                    if 300 <= status < 400: raise ScholarlyError(provider, 'redirect_rejected', 'Scholarly API redirect rejected; no external URL was followed.')
                    if status != 200: raise ScholarlyError(provider, 'unavailable', f'{provider} returned HTTP {status}. Other providers may still be usable.')
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > 2000000: raise ScholarlyError(provider, 'response_limit', 'Scholarly response exceeded the 2 MB safety limit.')
                        if budget.remaining()<=0:raise ScholarlyError(provider,'budget','Scholarly retrieval runtime limit reached.')
                    try: payload = json.loads(body)
                    except (ValueError, UnicodeError): raise ScholarlyError(provider, 'invalid_response', f'{provider} returned invalid JSON.')
            if not isinstance(payload,dict):raise ScholarlyError(provider,'invalid_response','Scholarly API returned an unexpected response envelope.')
            payload['_retrieved_at']=now()
            from app.main import transaction
            with transaction() as s:
                s.execute(delete(LiteratureCache).where(LiteratureCache.expires_at<now()))
                stale=s.scalars(select(LiteratureCache.key).order_by(LiteratureCache.created_at.desc()).offset(255)).all()
                if stale:s.execute(delete(LiteratureCache).where(LiteratureCache.key.in_(stale)))
                old = s.get(LiteratureCache, cache_key)
                expiry = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
                if old: old.payload = payload; old.created_at = now(); old.expires_at = expiry
                else: s.add(LiteratureCache(key=cache_key, provider=provider, payload=payload, expires_at=expiry))
            return payload
        except httpx.HTTPError:
            if attempt == 0 and budget.remaining() > 2: time.sleep(1); continue
            raise ScholarlyError(provider, 'network', f'{provider} could not be reached within the request timeout. Retry later.') from None
    raise ScholarlyError(provider, 'unavailable', f'{provider} is unavailable.')


def abstract_from_index(index):
    positions = {}
    for word, indices in list((index or {}).items())[:10000]:
        for position in indices[:1000]:
            if isinstance(position, int) and 0 <= position < 5000: positions[position] = word
    return text(' '.join(positions[k] for k in sorted(positions)))


def year(value):
    try: return int(value) if 1000 <= int(value) <= 2200 else None
    except (ValueError, TypeError): return None


def normalize_openalex(raw):
    work = str(raw.get('id', '')).rsplit('/', 1)[-1]
    if not re.fullmatch(r'W\d{1,16}', work): raise ValueError('Invalid returned OpenAlex identity')
    aliases = {'openalex': work}
    if raw.get('doi'): aliases['doi'] = doi(raw['doi'])
    for key in ['pmid', 'pmcid']:
        value = (raw.get('ids') or {}).get(key)
        if value:
            clean = str(value).rstrip('/').rsplit('/', 1)[-1]
            if key == 'pmid' and clean.isdigit(): aliases[key] = clean
            elif key == 'pmcid' and re.fullmatch(r'PMC\d+', clean): aliases[key] = clean
    location = raw.get('primary_location') or {}; oa = raw.get('best_oa_location') or {}
    abstract = abstract_from_index(raw.get('abstract_inverted_index'))
    return Paper(title=text(raw.get('title') or raw.get('display_name'), 2000), authors=[text((a.get('author') or {}).get('display_name'), 200) for a in raw.get('authorships', [])[:100]], year=year(raw.get('publication_year')), publication_date=raw.get('publication_date'), venue=text((location.get('source') or {}).get('display_name'), 500), identifiers=aliases, publisher_url=safe_link(location.get('landing_page_url')) or ('https://doi.org/' + aliases['doi'] if aliases.get('doi') else 'https://openalex.org/' + work), open_access_url=safe_link(oa.get('pdf_url') or oa.get('landing_page_url')), abstract=abstract, publication_type=str(raw.get('type') or '')[:150], provider='OpenAlex', retrieved_at=raw.get('_retrieved_at') or now(), provider_url='https://api.openalex.org/works/' + work, references=[str(v) for v in raw.get('referenced_works', [])[:50]], retraction_status='retracted' if raw.get('is_retracted') else 'not_flagged' if 'is_retracted' in raw else 'unknown', license=location.get('license'), access_level='abstract' if abstract else 'metadata')


def normalize_pmc(raw):
    aliases = {}
    if raw.get('doi'): aliases['doi'] = doi(raw['doi'])
    if raw.get('pmid'): aliases['pmid'] = str(raw['pmid'])
    if raw.get('source') == 'MED' and str(raw.get('id', '')).isdigit(): aliases['pmid'] = str(raw['id'])
    if raw.get('pmcid'): aliases['pmcid'] = str(raw['pmcid']).upper()
    if str(raw.get('id', '')).startswith('PMC'): aliases['pmcid'] = str(raw['id']).upper()
    if not aliases: raise ValueError('Europe PMC result has no supported persistent identifier')
    journal = (raw.get('journalInfo') or {}).get('journal') or {}
    abstract = text(raw.get('abstractText'))
    pubtypes = (raw.get('pubTypeList') or {}).get('pubType', [])
    source_id = aliases.get('pmid') or aliases.get('pmcid')
    link = 'https://europepmc.org/article/' + ('MED/' if aliases.get('pmid') else 'PMC/') + source_id
    urls = (raw.get('fullTextUrlList') or {}).get('fullTextUrl', [])
    oa = next((safe_link(v.get('url')) for v in urls if v.get('availabilityCode') == 'OA' and safe_link(v.get('url'))), None)
    return Paper(title=text(raw.get('title'), 2000), authors=[text(v.get('fullName') or v.get('collectiveName'), 200) for v in (raw.get('authorList') or {}).get('author', [])[:100]] or [text(raw.get('authorString'), 500)], year=year(raw.get('pubYear')), publication_date=raw.get('firstPublicationDate'), venue=text(journal.get('title') or raw.get('journalTitle'), 500), identifiers=aliases, publisher_url='https://doi.org/' + aliases['doi'] if aliases.get('doi') else link, open_access_url=oa, abstract=abstract, publication_type=', '.join(pubtypes)[:500], provider='Europe PMC', retrieved_at=raw.get('_retrieved_at') or now(), provider_url=link, retraction_status='retracted' if any('retract' in v.lower() and 'retraction of' not in v.lower() for v in pubtypes) else 'unknown', access_level='abstract' if abstract else 'metadata')


def normalize_crossref(raw):
    value = doi(raw.get('DOI'))
    parts = (raw.get('published') or raw.get('issued') or {}).get('date-parts', [[]])[0]
    abstract = text(raw.get('abstract'))
    corrections = [str(v.get('DOI')) for v in raw.get('update-to', [])[:20] if v.get('DOI')]
    return Paper(title=text((raw.get('title') or [''])[0], 2000), authors=[text(' '.join(filter(None, [a.get('given'), a.get('family')])) or a.get('name'), 200) for a in raw.get('author', [])[:100]], year=year(parts[0] if parts else None), publication_date='-'.join(str(v) for v in parts) or None, venue=text((raw.get('container-title') or [''])[0], 500), identifiers={'doi': value}, publisher_url='https://doi.org/' + value, open_access_url=None, abstract=abstract, publication_type=str(raw.get('type') or '')[:150], provider='Crossref', retrieved_at=raw.get('_retrieved_at') or now(), provider_url='https://api.crossref.org/works/' + quote(value, safe=''), references=[doi(v['DOI']) for v in raw.get('reference', [])[:50] if v.get('DOI') and re.fullmatch(r'10\.\d{4,9}/\S+', v['DOI'])], retraction_status='retraction_notice' if any(v.get('type') == 'retraction' for v in raw.get('update-to', [])) else 'unknown', corrections=corrections, license=next((safe_link(v.get('URL')) for v in raw.get('license', []) if safe_link(v.get('URL'))), None), access_level='abstract' if abstract else 'metadata')


class ScholarlyProvider(Protocol):
    name: str
    def search(self, query: str, budget: RequestBudget) -> list[Paper]: ...
    def resolve(self, kind: str, value: str, budget: RequestBudget) -> Paper: ...


def normalize_many(items, normalizer, retrieved_at=None):
    results = []
    for item in items[:5]:
        try: results.append(normalizer({**item,'_retrieved_at':retrieved_at}))
        except (ValueError, TypeError, KeyError): continue
    return results


class OpenAlex:
    name = 'OpenAlex'
    def search(self, query, budget):
        data=request_json(self.name,'/works',{'search':query,'per_page':5},budget)
        return normalize_many(data.get('results',[]),normalize_openalex,data.get('_retrieved_at'))
    def resolve(self, kind, value, budget):
        path = '/works/' + (value if kind == 'openalex' else quote('https://doi.org/' + value, safe=''))
        result=normalize_openalex(request_json(self.name, path, {}, budget))
        if result.identifiers.get(kind)!=value:raise ScholarlyError(self.name,'identity_mismatch','The returned OpenAlex identity did not match the requested identifier.')
        return result


class EuropePMC:
    name = 'Europe PMC'
    def search(self, query, budget):
        data=request_json(self.name,'/search',{'query':query,'format':'json','resultType':'core','pageSize':5},budget)
        return normalize_many(data.get('resultList',{}).get('result',[]),normalize_pmc,data.get('_retrieved_at'))
    def resolve(self, kind, value, budget):
        query = {'doi': f'DOI:"{value}"', 'pmid': f'EXT_ID:{value} AND SRC:MED', 'pmcid': f'PMCID:{value}'}[kind]
        items = self.search(query, budget)
        result = next((p for p in items if p.identifiers.get(kind) == value), None)
        if not result: raise ScholarlyError(self.name, 'not_found', 'Europe PMC could not verify the exact identifier.')
        return result


class Crossref:
    name = 'Crossref'
    def search(self, query, budget):
        data=request_json(self.name,'/works',{'query.bibliographic':query,'rows':5},budget)
        return normalize_many(data.get('message',{}).get('items',[]),normalize_crossref,data.get('_retrieved_at'))
    def resolve(self, kind, value, budget):
        if kind != 'doi': raise ScholarlyError(self.name, 'unsupported', 'Crossref resolves DOI identifiers only.')
        data=request_json(self.name,'/works/'+quote(value,safe=''),{},budget)
        result=normalize_crossref({**data['message'],'_retrieved_at':data.get('_retrieved_at')})
        if result.identifiers['doi'] != value: raise ScholarlyError(self.name, 'identity_mismatch', 'The returned DOI did not match the requested identifier.')
        return result


PROVIDERS = {'OpenAlex': OpenAlex(), 'Europe PMC': EuropePMC(), 'Crossref': Crossref()}
