"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export interface LearningRef {
  id: number;
  url: string | null;
  creator: string | null;
  platform: string | null;
  category: string;
  title: string | null;
  notes: string | null;
  saved_at: string;
}

export function ReferenceCard({
  ref: item,
  onCopyToIdeation,
  onDelete,
}: {
  ref: LearningRef;
  onCopyToIdeation?: (ref: LearningRef) => void;
  onDelete?: (id: number) => void;
}) {
  return (
    <Card size="sm" className="flex flex-col gap-2">
      <CardHeader>
        <CardTitle className="line-clamp-2">{item.title ?? "(untitled)"}</CardTitle>
        <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground pt-1">
          {item.creator && <Badge variant="outline">{item.creator}</Badge>}
          {item.platform && <Badge variant="secondary">{item.platform}</Badge>}
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {item.notes && (
          <p className="text-xs text-muted-foreground line-clamp-4 whitespace-pre-line">
            {item.notes}
          </p>
        )}
        <div className="flex flex-wrap gap-1.5 pt-1">
          {item.url && (
            <a href={item.url} target="_blank" rel="noreferrer">
              <Button size="xs" variant="outline">
                Open
              </Button>
            </a>
          )}
          {onCopyToIdeation && (
            <Button
              size="xs"
              variant="outline"
              onClick={() => onCopyToIdeation(item)}
            >
              Copy to Ideation
            </Button>
          )}
          {onDelete && (
            <Button
              size="xs"
              variant="ghost"
              onClick={() => onDelete(item.id)}
            >
              Delete
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
