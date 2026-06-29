import { redirect } from "next/navigation";

/**
 * The Agents gallery has been replaced by the Work Mode selector on the
 * main chat page. Redirect any legacy links to the new conversation page.
 */
export default function AgentsPage() {
  redirect("/workspace/chats/new");
}
