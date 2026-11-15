import { ProjectWorkspace } from "@/components/project-workspace";
export default async function SettingsPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ProjectWorkspace id={id} view="settings" />;
}
