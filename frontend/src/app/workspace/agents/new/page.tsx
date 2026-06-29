import { redirect } from "next/navigation";

/**
 * The standalone Agent creation flow has been replaced by the Work Mode
 * system. Redirect any legacy links to the new conversation page.
 */
export default function NewAgentPage() {
  redirect("/workspace/chats/new");
}
