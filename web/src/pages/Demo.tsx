import { useMutation, useQuery } from "@tanstack/react-query";
import { Download, FileUp, Loader2, PlayCircle } from "lucide-react";
import { useRef, useState } from "react";
import { useNavigate } from "react-router";
import { api } from "../lib/api";

export function Demo() {
  const navigate = useNavigate();
  const samples = useQuery({ queryKey: ["samples"], queryFn: api.samples });
  const health = useQuery({ queryKey: ["health"], queryFn: api.health });
  const uploadsAllowed = health.data?.allow_uploads ?? true;
  const [file, setFile] = useState<File | null>(null);
  const [periodEnd, setPeriodEnd] = useState("");
  const [drag, setDrag] = useState(false);
  const input = useRef<HTMLInputElement>(null);

  const submit = useMutation({
    mutationFn: async (args: { sample?: string; file?: File }) => {
      const form = new FormData();
      if (args.sample) form.append("sample", args.sample);
      if (args.file) form.append("file", args.file);
      if (periodEnd) form.append("period_end", periodEnd);
      return api.submit(form);
    },
    onSuccess: (res) => navigate(`/s/${res.id}`),
  });

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <h1 className="text-3xl font-semibold tracking-tight">Run a submission</h1>
      <p className="mt-2 max-w-2xl text-muted">
        Start with a sample export of the fictional Example Islamic Bank, or upload your own synthetic file.
        Daleel will show how it reads and transforms the file, then calculate and explain the results.
      </p>

      <h2 className="mt-10 text-sm font-semibold uppercase tracking-wider text-faint">Sample exports</h2>
      <div className="mt-3 grid gap-4 md:grid-cols-2">
        {(samples.data ?? []).map((s) => (
          <div key={s.name} className="flex flex-col rounded-xl border border-line bg-panel p-5">
            <div className="flex items-center justify-between gap-2">
              <h3 className="font-semibold">{s.title}</h3>
              <span className={`rounded px-2 py-0.5 text-xs font-medium ${s.name === "stressed" ? "bg-fail-soft text-fail" : "bg-pass-soft text-pass"}`}>
                {s.name === "stressed" ? "Planted breaches" : "Healthy"}
              </span>
            </div>
            <p className="mt-2 flex-1 text-sm leading-relaxed text-muted">{s.description}</p>
            <div className="mt-4 flex flex-wrap items-center gap-3">
              <button
                onClick={() => submit.mutate({ sample: s.name })}
                disabled={submit.isPending}
                className="inline-flex items-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-panel hover:opacity-90 disabled:opacity-50"
              >
                {submit.isPending && submit.variables?.sample === s.name ? <Loader2 size={16} className="animate-spin" /> : <PlayCircle size={16} />}
                Run this sample
              </button>
              <a href={api.sampleUrl(s.name)} className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-ink">
                <Download size={15} /> See the raw file
              </a>
            </div>
          </div>
        ))}
        {samples.isLoading && <p className="text-sm text-muted">Loading samples…</p>}
      </div>

      {uploadsAllowed && <>
      <h2 className="mt-10 text-sm font-semibold uppercase tracking-wider text-faint">Or upload a file</h2>
      <div
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); setFile(e.dataTransfer.files[0] ?? null); }}
        className={`mt-3 rounded-xl border-2 border-dashed p-8 text-center transition ${drag ? "border-brand bg-brand-soft" : "border-line bg-panel"}`}
      >
        <FileUp className="mx-auto text-faint" size={28} aria-hidden />
        <p className="mt-3 text-sm text-muted">
          Drop an .xlsx, .csv or .parquet file here, or{" "}
          <button className="font-medium text-brand underline-offset-2 hover:underline" onClick={() => input.current?.click()}>choose a file</button>.
        </p>
        <p className="mt-1 text-xs text-faint">Up to 50 MB. Use synthetic or anonymised data only: this is a public demo.</p>
        <input ref={input} type="file" accept=".xlsx,.csv,.txt,.parquet" className="hidden" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
        {file && (
          <div className="mx-auto mt-5 flex max-w-md flex-col items-stretch gap-3 text-left">
            <p className="truncate rounded-md border border-line bg-surface px-3 py-2 font-mono text-xs">{file.name} · {(file.size / 1024).toFixed(0)} KB</p>
            <label className="text-xs text-muted">
              Reporting date (only needed if the file does not say)
              <input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} className="mt-1 block w-full rounded-md border border-line bg-panel px-3 py-2 text-sm text-ink" />
            </label>
            <button
              onClick={() => submit.mutate({ file })}
              disabled={submit.isPending}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-medium text-panel hover:opacity-90 disabled:opacity-50"
            >
              {submit.isPending ? <Loader2 size={16} className="animate-spin" /> : <FileUp size={16} />} Upload and process
            </button>
          </div>
        )}
      </div>
      </>}
      {submit.isError && <p role="alert" className="mt-4 rounded-md bg-fail-soft px-3 py-2 text-sm text-fail">{(submit.error as Error).message}</p>}
    </div>
  );
}
