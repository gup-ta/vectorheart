import type { Metadata } from "next";
import { WorkspaceProvider } from "@/components/workspace-provider";
import { Settings } from "@/components/settings";
import "@xyflow/react/dist/style.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "VectorHeart — A place for discovery",
  description: "A thoughtful workspace for scientific discovery and human–AI research.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><WorkspaceProvider>{children}<Settings /></WorkspaceProvider></body></html>;
}
