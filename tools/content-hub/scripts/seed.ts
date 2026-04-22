import { seedIdeation } from "./seed-ideation";

async function main() {
  try {
    const ideation = seedIdeation();
    console.log("[seed] ideation:", ideation);
  } catch (err) {
    console.error("[seed] agent B (ideation) failed:", err);
  }

  // --- Agent C: Calendar + Library ---
  try {
    const { seedCalendar } = await import("./seed-calendar");
    seedCalendar();
  } catch (err) {
    console.error("[seed] agent C (calendar) failed:", err);
  }

  // Agent D will append below.
  try {
    const { seedLearning } = await import("./seed-learning");
    const learning = seedLearning();
    console.log("[seed] learning:", learning);
  } catch (err) {
    console.error("[seed] agent D (learning) failed:", err);
  }
}

main().catch((err) => {
  console.error("[seed] fatal:", err);
  process.exit(1);
});
