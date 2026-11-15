import Link from "next/link";
import { Orbit } from "lucide-react";

export function Brand() {
  return <Link href="/" className="brand" aria-label="VectorHeart home"><Orbit size={25} strokeWidth={1.35} /><span>VECTORHEART</span><span className="version">0.1</span></Link>;
}
