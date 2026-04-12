"use client";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";

export default function ResultsPage() {
  const params = useParams();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (params?.id) {
      fetch(`/api/backend/valuation/${params.id}`)
        .then(r => r.json())
        .then(d => { setData(d); setLoading(false); })
        .catch(() => setLoading(false));
    }
  }, [params?.id]);

  if (loading) return <div className="p-8 text-center">Loading valuation...</div>;
  if (!data) return <div className="p-8 text-center">Valuation not found.</div>;

  return (
    <main className="max-w-4xl mx-auto p-8">
      <h1 className="text-2xl font-bold mb-4">{data.address}</h1>
      <div className="bg-white rounded-2xl border p-6 mb-4">
        <p className="text-sm text-gray-500">Estimated Value</p>
        <p className="text-3xl font-bold">£{data.estimated_value?.toLocaleString()}</p>
      </div>
      <pre className="text-xs bg-gray-50 p-4 rounded overflow-auto">{JSON.stringify(data, null, 2)}</pre>
    </main>
  );
}
