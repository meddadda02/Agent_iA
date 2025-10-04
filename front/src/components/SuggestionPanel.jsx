import React from "react";

export default function SuggestionPanel({ suggestions }) {
  if (!suggestions || suggestions.length === 0)
    return <div className="text-gray-500 p-2">Aucune suggestion trouvée.</div>;

  return (
    <div className="space-y-4 bg-white p-4 rounded-xl shadow">
      <h3 className="text-lg font-semibold text-gray-800">Suggestions automatiques</h3>
      {suggestions.map((s) => (
        <div key={s.id} className="border rounded-lg p-3">
          <div className="flex justify-between">
            <div>
              <p className="font-semibold">{s.short}</p>
              <p className="text-xs text-gray-500">Sévérité : {s.severity}</p>
            </div>
          </div>
          {s.explanation && <p className="mt-2 text-sm">{s.explanation}</p>}
          {s.actionable_steps && (
            <ul className="list-disc list-inside text-sm mt-2">
              {s.actionable_steps.map((a, i) => <li key={i}>{a}</li>)}
            </ul>
          )}
          {s.example_rewrite && (
            <pre className="bg-gray-100 p-2 mt-2 rounded text-sm">{s.example_rewrite}</pre>
          )}
        </div>
      ))}
    </div>
  );
}
