export default function ReviewSection({ title, content }: { title: string; content: string }) {
  return (
    <div className="space-y-4">
      <h4 className="font-semibold text-sm">{title}</h4>
      <p className="whitespace-pre-wrap text-sm text-muted-foreground bg-muted p-3 rounded-md">{content}</p>
    </div>
  );
}
