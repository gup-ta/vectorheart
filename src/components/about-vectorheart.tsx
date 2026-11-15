"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowUpRight, X } from "lucide-react";

const capabilities = [
  ["Research Journal", "A free-form record of ideas, observations, doubts, experiments, and discoveries. Your original writing stays yours."],
  ["Living Research Graph", "AI reconstructs the understanding in your records. Inspect its sources, correct its interpretation, and preserve your changes."],
  ["AI Accelerate", "Review new hypotheses, conceptual links, challenges, and experiments directly on the graph. Suggestions remain proposals until you accept them."],
  ["Scientific Kernel", "Versioned research objects, evidence, approvals, and provenance preserve what changed, why it changed, and where it came from."],
  ["Autonomous Investigation", "Bounded investigations use registered tools. Computational experiments pause for human approval and return actual results for further reasoning."],
  ["Literature Intelligence", "Discover real scholarly records and inspect available abstracts. Review source-grounded interpretations while keeping published findings distinct from local experiments."],
];

export function AboutVectorHeart() {
  const [open, setOpen] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => { if (open) dialog.current?.showModal(); }, [open]);
  return <>
    <button className="text-button about-control" onClick={() => setOpen(true)}>Our vision <ArrowUpRight size={14} /></button>
    {open && <dialog ref={dialog} className="vision-dialog" aria-labelledby="vision-title" onCancel={() => setOpen(false)} onClick={event => { if (event.target === event.currentTarget) setOpen(false); }}>
      <div className="vision-topline"><span className="eyebrow">ABOUT VECTORHEART</span><button className="icon-button" aria-label="Close our vision" onClick={() => setOpen(false)}><X size={20} /></button></div>
      <div className="vision-content">
        <p className="vision-kicker">Human curiosity. Computational possibility.</p>
        <h2 id="vision-title">Understanding,<br />still becoming.</h2>
        <p className="vision-lead">Scientific understanding can be a persistent, evolving, inspectable, and experimentally challengeable system.</p>
        <p>VectorHeart explores a new relationship between humans, artificial intelligence, and scientific discovery. The researcher writes freely. AI reconstructs the understanding in those records. The researcher corrects it. New ideas become proposals; scientific tools and literature help investigate them. The journey remains inspectable.</p>
        <div className="vision-cycle" aria-label="Research cycle"><span>Write</span><span aria-hidden="true">→</span><span>Understand</span><span aria-hidden="true">→</span><span>Challenge</span><span aria-hidden="true">→</span><span>Discover</span></div>
        <section aria-labelledby="vision-current"><p className="eyebrow">THE CURRENT INSTRUMENT</p><h3 id="vision-current">A place for ideas to become investigations.</h3><div className="vision-capabilities">{capabilities.map(([title, description], index) => <article key={title}><span className="vision-number">0{index + 1}</span><h4>{title}</h4><p>{description}</p></article>)}</div><p className="vision-caveat">Model features require a configured provider. Executable experiments are limited to registered tools; the current causal lab is a synthetic demonstration. Literature interpretation is bounded by the source content actually retrieved. Acceptance never means scientific verification.</p></section>
        <section className="vision-future" aria-labelledby="vision-next"><p className="eyebrow">OUR VISION · FUTURE POSSIBILITIES</p><h3 id="vision-next">The Research That Comes Next</h3><p>Beyond the current implementation, we imagine:</p><ul>
          <li>Scientific memory spanning years, preserving the evolution of ideas.</li>
          <li>AI that finds contradictions and missing explanations across vast research graphs.</li>
          <li>Connections to laboratory instruments, simulations, databases, and scientific computing.</li>
          <li>Multimodal models that interpret equations, visual data, and complex experimental records.</li>
          <li>Specialized scientific agents collaborating under researcher supervision.</li>
          <li>Research projects connecting their knowledge while preserving authorship and provenance.</li>
        </ul></section>
        <blockquote className="vision-closing">Scientific discovery should not end when an experiment is recorded. Every result should become the beginning of the next question.</blockquote>
      </div>
    </dialog>}
  </>;
}
