import { ProjectNotebook } from "@/components/project-notebook";

export default async function ProjectPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ProjectNotebook id={id} />;
}
