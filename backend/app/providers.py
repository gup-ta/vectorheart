"""Proposal-only boundary; state and executor do not depend on providers."""
from typing import Protocol
from pydantic import BaseModel
class ProposalProvider(Protocol):
    def formalize_hypothesis(self, payload: dict) -> BaseModel: ...
    def propose_experiment(self, payload: dict) -> BaseModel: ...
    def propose_revision(self, payload: dict) -> BaseModel: ...
class ManualProvider:
    def formalize_hypothesis(self,payload):
        from app.main import Construct
        return Construct.model_validate(payload)
    def propose_experiment(self,payload):
        from app.main import TestHypothesis
        return TestHypothesis.model_validate(payload)
    def propose_revision(self,payload):
        from app.main import Modify
        return Modify.model_validate(payload)
