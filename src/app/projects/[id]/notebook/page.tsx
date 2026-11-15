import { ProjectWorkspace } from "@/components/project-workspace";
export default async function NotebookPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ProjectWorkspace id={id} view="notebook" />;
}
