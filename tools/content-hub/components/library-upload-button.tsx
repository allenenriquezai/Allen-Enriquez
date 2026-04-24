"use client";

import * as React from "react";
import { Plus } from "lucide-react";
import { LibraryAddDialog } from "@/components/library-add-dialog";

export function LibraryUploadButton() {
  const [open, setOpen] = React.useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-semibold transition-colors"
        style={{ background: "var(--brand)", color: "#000" }}
      >
        <Plus className="size-4" />
        Upload
      </button>
      {open && (
        <LibraryAddDialog
          onDone={() => {
            setOpen(false);
            window.location.reload();
          }}
        />
      )}
    </>
  );
}
