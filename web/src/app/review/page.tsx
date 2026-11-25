import GpuLoadSummary from "@/features/gpu/GpuLoadSummary";
import ResultsPanel from "@/features/review/ResultsPanel";
import ReviewForm from "@/features/review/ReviewForm";
import ReviewQueue from "@/features/review/ReviewQueue";

export default function ReviewPage() {
  return (
    <>
      <ReviewForm />
      <ReviewQueue />
      <GpuLoadSummary />
      <ResultsPanel />
    </>
  );
}
