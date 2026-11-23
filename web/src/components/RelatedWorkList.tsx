import type { RelatedPaper } from "@/lib/types";

function byline(paper: RelatedPaper): string {
  const all = paper.authors ?? [];
  const authors = all.slice(0, 4).join(", ") + (all.length > 4 ? " et al." : "");
  return [authors, paper.year].filter(Boolean).join(" · ");
}

/** The arXiv papers the reviewer was shown, with the refs ([R1], ...) the review cites them by. */
export default function RelatedWorkList({ papers }: { papers: RelatedPaper[] }) {
  return (
    <div className="space-y-4">
      <h4 className="font-semibold text-sm">📚 Related Work Found on arXiv</h4>
      <ol className="space-y-2 bg-muted p-3 rounded-md text-sm" aria-label="Related work">
        {papers.map((paper) => (
          <li key={paper.ref} className="flex gap-2">
            <span className="font-mono text-xs text-primary shrink-0 pt-0.5">[{paper.ref}]</span>
            <div className="min-w-0">
              <a href={paper.url} target="_blank" rel="noopener noreferrer" className="font-medium hover:underline">
                {paper.title}
              </a>
              <p className="text-xs text-muted-foreground">{byline(paper)}</p>
              {paper.relation && <p className="text-muted-foreground mt-1">{paper.relation}</p>}
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
