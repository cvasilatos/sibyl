import GpuLoadSummary from "@/features/gpu/GpuLoadSummary";
import ResultsPanel from "@/features/review/ResultsPanel";
import ReviewForm from "@/features/review/ReviewForm";

export default function ReviewPage() {
  return (
    <>
      <ReviewForm />
      <GpuLoadSummary />
      <ResultsPanel />
    </>
  );
}
