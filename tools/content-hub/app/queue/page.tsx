import { redirect } from "next/navigation";

export default function QueuePage() {
  redirect("/calendar?tab=queue");
}
