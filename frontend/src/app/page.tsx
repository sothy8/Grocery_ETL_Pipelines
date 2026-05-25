"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useCallback, useEffect, useMemo, useState } from "react";

type DashboardResponse = {
  refreshed_at: string;
  metrics: {
    total_records: number;
    avg_sales: number;
    total_sales: number;
    avg_rating: number;
    model_r2: number;
  };
  filters: {
    item_type: string[];
    outlet_type: string[];
    outlet_location_type: string[];
    outlet_size: string[];
    item_fat_content: string[];
    sales_min: number;
    sales_max: number;
  };
  charts: {
    sales_by_item_type: {
      item_type: string;
      total_sales: number;
      avg_sales: number;
      count: number;
    }[];
    sales_by_outlet_type: { outlet_type: string; total_sales: number; count: number }[];
    sales_by_location_type: {
      outlet_location_type: string;
      total_sales: number;
      count: number;
    }[];
    sales_by_outlet_size: { outlet_size: string; total_sales: number; count: number }[];
    sales_by_fat_content: {
      item_fat_content: string;
      total_sales: number;
      avg_sales: number;
      count: number;
    }[];
    sales_by_year: {
      outlet_establishment_year: number;
      total_sales: number;
      count: number;
    }[];
    sales_distribution: { bin_start: number; bin_end: number; count: number }[];
  };
  tables: {
    top_products: {
      item_identifier: string;
      item_type: string;
      total_sales: number;
      avg_rating: number;
    }[];
    sample_rows: Record<string, number | string | null>[];
  };
  predictions: {
    rows: Record<string, number | string | null>[];
    avg_predicted_total_sales: number;
    sum_predicted_total_sales: number;
  };
};

type FilterState = {
  item_type: string[];
  outlet_type: string[];
  outlet_location_type: string[];
  outlet_size: string[];
  item_fat_content: string[];
  sales_min: number;
  sales_max: number;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8000";
const PIE_COLORS = ["#1d4ed8", "#f97316", "#0f766e", "#a855f7", "#9333ea", "#22c55e"];

const formatCurrency = (value: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(
    value,
  );

const formatCurrencyPrecise = (value: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 }).format(
    value,
  );

const formatNumber = (value: number) => new Intl.NumberFormat("en-US").format(value);

const delay = (milliseconds: number) => new Promise((resolve) => setTimeout(resolve, milliseconds));

const buildQuery = (filters: FilterState | null) => {
  if (!filters) return "";
  const params = new URLSearchParams();
  filters.item_type.forEach((value) => params.append("item_type", value));
  filters.outlet_type.forEach((value) => params.append("outlet_type", value));
  filters.outlet_location_type.forEach((value) => params.append("outlet_location_type", value));
  filters.outlet_size.forEach((value) => params.append("outlet_size", value));
  filters.item_fat_content.forEach((value) => params.append("item_fat_content", value));
  params.set("sales_min", filters.sales_min.toString());
  params.set("sales_max", filters.sales_max.toString());
  params.set("limit", "50");
  return params.toString();
};

const MultiSelect = ({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: string[];
  value: string[];
  onChange: (next: string[]) => void;
}) => {
  return (
    <label className="flex flex-col gap-2 text-sm text-[color:var(--ink-muted)]">
      <span className="text-xs uppercase tracking-[0.2em]">{label}</span>
      <select
        multiple
        className="h-28 rounded-2xl border border-black/10 bg-[color:var(--surface)] px-3 py-2 text-sm text-[color:var(--foreground)] shadow-[0_8px_20px_rgba(0,0,0,0.04)] focus:outline-none focus:ring-2 focus:ring-[color:var(--ring)]"
        value={value}
        onChange={(event) =>
          onChange(Array.from(event.currentTarget.selectedOptions, (option) => option.value))
        }
      >
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
};

export default function Home() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [filters, setFilters] = useState<FilterState | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const query = buildQuery(filters);
      const url = `${API_BASE}/dashboard-data${query ? `?${query}` : ""}`;
      let response: Response | null = null;
      let lastError: unknown = null;

      for (let attempt = 1; attempt <= 5; attempt += 1) {
        try {
          response = await fetch(url, { cache: "no-store" });
          if (response.ok) {
            break;
          }
          lastError = new Error(`API error: ${response.status}`);
        } catch (err) {
          lastError = err;
        }

        if (attempt < 5) {
          await delay(1000 * attempt);
        }
      }

      if (!response) {
        throw lastError instanceof Error ? lastError : new Error("Failed to fetch dashboard data");
      }

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
      }

      const payload = (await response.json()) as DashboardResponse;
      setData(payload);
      if (!filters) {
        setFilters({
          item_type: payload.filters.item_type,
          outlet_type: payload.filters.outlet_type,
          outlet_location_type: payload.filters.outlet_location_type,
          outlet_size: payload.filters.outlet_size,
          item_fat_content: payload.filters.item_fat_content,
          sales_min: payload.filters.sales_min,
          sales_max: payload.filters.sales_max,
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void fetchData();
    }, 0);
    return () => window.clearTimeout(timer);
  }, [fetchData]);

  useEffect(() => {
    if (!autoRefresh) return;
    const timer = setInterval(() => {
      void fetchData();
    }, 15000);
    return () => clearInterval(timer);
  }, [autoRefresh, fetchData]);

  const hasData = data && filters;

  const predictionsSummary = useMemo(() => {
    if (!data) return null;
    return {
      avg: data.predictions.avg_predicted_total_sales,
      total: data.predictions.sum_predicted_total_sales,
    };
  }, [data]);

  return (
    <div className="min-h-screen">
      <header className="relative overflow-hidden border-b border-black/5">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(232,112,57,0.12),_transparent_60%)]" />
        <div className="relative mx-auto flex max-w-6xl flex-col gap-6 px-6 py-12">
          <div className="flex items-center justify-between gap-6 flex-wrap">
            <div className="flex flex-col gap-3">
              <span className="text-xs uppercase tracking-[0.4em] text-[color:var(--ink-muted)]">
                Grocery Pipeline
              </span>
              <h1 className="text-4xl font-semibold leading-tight text-[color:var(--foreground)] md:text-5xl">
                Grocery Sales Command Center
              </h1>
              <p className="max-w-2xl text-base text-[color:var(--ink-muted)] md:text-lg">
                Real-time sales signals, auto-refreshing every 15 seconds with predictive insights powered by FastAPI.
              </p>
            </div>
            <div className="rounded-3xl bg-[color:var(--surface)] px-5 py-4 shadow-[0_15px_30px_rgba(0,0,0,0.08)]">
              <div className="text-xs uppercase tracking-[0.3em] text-[color:var(--ink-muted)]">
                Refresh
              </div>
              <div className="mt-2 flex items-center gap-3">
                <button
                  className={`rounded-full px-4 py-2 text-sm font-medium transition ${
                    autoRefresh
                      ? "bg-[color:var(--accent)] text-white shadow-[0_10px_24px_rgba(232,112,57,0.35)]"
                      : "bg-black/5 text-[color:var(--foreground)]"
                  }`}
                  onClick={() => setAutoRefresh((prev) => !prev)}
                  type="button"
                >
                  {autoRefresh ? "Auto-refresh on" : "Auto-refresh off"}
                </button>
                <span className="text-xs text-[color:var(--ink-muted)]">15s cadence</span>
              </div>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-4">
            {[
              { label: "Records", value: data?.metrics.total_records ?? 0 },
              { label: "Average Sales", value: data ? formatCurrencyPrecise(data.metrics.avg_sales) : "-" },
              { label: "Total Sales", value: data ? formatCurrency(data.metrics.total_sales) : "-" },
              { label: "Model R²", value: data ? data.metrics.model_r2.toFixed(3) : "-" },
            ].map((item) => (
              <div
                key={item.label}
                className="rounded-3xl border border-black/10 bg-[color:var(--surface)] p-5 shadow-[0_12px_30px_rgba(0,0,0,0.06)]"
              >
                <div className="text-xs uppercase tracking-[0.3em] text-[color:var(--ink-muted)]">
                  {item.label}
                </div>
                <div className="mt-3 text-2xl font-semibold text-[color:var(--foreground)]">
                  {typeof item.value === "number" ? formatNumber(item.value) : item.value}
                </div>
              </div>
            ))}
          </div>
        </div>
      </header>

      <main className="mx-auto flex max-w-6xl flex-col gap-10 px-6 py-10">
        <section className="grid gap-6 lg:grid-cols-[1.2fr_2fr]">
          <div className="rounded-3xl border border-black/10 bg-[color:var(--surface)] p-6 shadow-[0_18px_40px_rgba(0,0,0,0.08)]">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Filters</h2>
              <button
                type="button"
                className="text-xs uppercase tracking-[0.3em] text-[color:var(--accent-strong)]"
                onClick={() => {
                  if (!data) return;
                  setFilters({
                    item_type: data.filters.item_type,
                    outlet_type: data.filters.outlet_type,
                    outlet_location_type: data.filters.outlet_location_type,
                    outlet_size: data.filters.outlet_size,
                    item_fat_content: data.filters.item_fat_content,
                    sales_min: data.filters.sales_min,
                    sales_max: data.filters.sales_max,
                  });
                }}
              >
                Reset
              </button>
            </div>
            <div className="mt-6 grid gap-4">
              {hasData ? (
                <>
                  <MultiSelect
                    label="Item Type"
                    options={data.filters.item_type}
                    value={filters.item_type}
                    onChange={(value) => setFilters({ ...filters, item_type: value })}
                  />
                  <MultiSelect
                    label="Outlet Type"
                    options={data.filters.outlet_type}
                    value={filters.outlet_type}
                    onChange={(value) => setFilters({ ...filters, outlet_type: value })}
                  />
                  <MultiSelect
                    label="Location Type"
                    options={data.filters.outlet_location_type}
                    value={filters.outlet_location_type}
                    onChange={(value) => setFilters({ ...filters, outlet_location_type: value })}
                  />
                  <MultiSelect
                    label="Outlet Size"
                    options={data.filters.outlet_size}
                    value={filters.outlet_size}
                    onChange={(value) => setFilters({ ...filters, outlet_size: value })}
                  />
                  <MultiSelect
                    label="Fat Content"
                    options={data.filters.item_fat_content}
                    value={filters.item_fat_content}
                    onChange={(value) => setFilters({ ...filters, item_fat_content: value })}
                  />
                  <div className="grid gap-3 rounded-2xl border border-black/10 bg-[color:var(--surface-muted)] p-4">
                    <div className="text-xs uppercase tracking-[0.3em] text-[color:var(--ink-muted)]">Sales Range</div>
                    <div className="flex items-center gap-3">
                      <input
                        type="number"
                        className="w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm"
                        value={filters.sales_min}
                        onChange={(event) =>
                          setFilters({ ...filters, sales_min: Number(event.target.value) || 0 })
                        }
                      />
                      <span className="text-xs text-[color:var(--ink-muted)]">to</span>
                      <input
                        type="number"
                        className="w-full rounded-xl border border-black/10 bg-white px-3 py-2 text-sm"
                        value={filters.sales_max}
                        onChange={(event) =>
                          setFilters({ ...filters, sales_max: Number(event.target.value) || 0 })
                        }
                      />
                    </div>
                  </div>
                </>
              ) : (
                <div className="text-sm text-[color:var(--ink-muted)]">Waiting for data...</div>
              )}
            </div>
          </div>

          <div className="grid gap-6">
            <div className="rounded-3xl border border-black/10 bg-[color:var(--surface)] p-6 shadow-[0_18px_40px_rgba(0,0,0,0.08)]">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-semibold">Sales by Item Type</h2>
                <span className="text-xs text-[color:var(--ink-muted)]">
                  {data?.refreshed_at ? new Date(data.refreshed_at).toLocaleTimeString() : "-"}
                </span>
              </div>
              <div className="mt-4 h-72 min-h-[18rem] w-full">
                <ResponsiveContainer width="100%" height="100%" minHeight={240} minWidth={0}>
                  <BarChart data={data?.charts.sales_by_item_type ?? []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                    <XAxis dataKey="item_type" tick={{ fontSize: 10 }} interval={0} angle={-20} height={60} />
                    <YAxis tickFormatter={(value) => formatNumber(value)} />
                    <Tooltip formatter={(value) => typeof value === "number" ? formatCurrencyPrecise(value) : value} />
                    <Bar dataKey="total_sales" fill="#1d4ed8" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="grid gap-6 md:grid-cols-2">
              <div className="rounded-3xl border border-black/10 bg-[color:var(--surface)] p-6 shadow-[0_18px_40px_rgba(0,0,0,0.08)]">
                <h2 className="text-lg font-semibold">Outlet Mix</h2>
                <div className="mt-4 h-60 min-h-[15rem] w-full">
                  <ResponsiveContainer width="100%" height="100%" minHeight={220} minWidth={0}>
                    <PieChart>
                      <Pie
                        data={data?.charts.sales_by_outlet_type ?? []}
                        dataKey="total_sales"
                        nameKey="outlet_type"
                        innerRadius={45}
                        outerRadius={90}
                      >
                        {(data?.charts.sales_by_outlet_type ?? []).map((_, index) => (
                          <Cell key={index} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => typeof value === "number" ? formatCurrencyPrecise(value) : value} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              <div className="rounded-3xl border border-black/10 bg-[color:var(--surface)] p-6 shadow-[0_18px_40px_rgba(0,0,0,0.08)]">
                <h2 className="text-lg font-semibold">Sales Distribution</h2>
                <div className="mt-4 h-60 min-h-[15rem] w-full">
                  <ResponsiveContainer width="100%" height="100%" minHeight={220} minWidth={0}>
                    <BarChart data={data?.charts.sales_distribution ?? []}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                      <XAxis dataKey="bin_start" tickFormatter={(value) => formatNumber(value)} />
                      <YAxis />
                      <Tooltip
                        formatter={(value) => typeof value === "number" ? formatNumber(value) : value}
                        labelFormatter={(label) => `From ${formatNumber(Number(label))}`}
                      />
                      <Bar dataKey="count" fill="#f97316" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="grid gap-6 md:grid-cols-2">
          <div className="rounded-3xl border border-black/10 bg-[color:var(--surface)] p-6 shadow-[0_18px_40px_rgba(0,0,0,0.08)]">
            <h2 className="text-lg font-semibold">Sales by Location</h2>
            <div className="mt-4 h-64 min-h-[16rem] w-full">
              <ResponsiveContainer width="100%" height="100%" minHeight={240} minWidth={0}>
                <BarChart data={data?.charts.sales_by_location_type ?? []} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                  <XAxis type="number" tickFormatter={(value) => formatNumber(value)} />
                  <YAxis type="category" dataKey="outlet_location_type" width={80} />
                  <Tooltip formatter={(value) => typeof value === "number" ? formatCurrencyPrecise(value) : value} />
                  <Bar dataKey="total_sales" fill="#0f766e" radius={[0, 8, 8, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="rounded-3xl border border-black/10 bg-[color:var(--surface)] p-6 shadow-[0_18px_40px_rgba(0,0,0,0.08)]">
            <h2 className="text-lg font-semibold">Outlet Year Trend</h2>
            <div className="mt-4 h-64 min-h-[16rem] w-full">
              <ResponsiveContainer width="100%" height="100%" minHeight={240} minWidth={0}>
                <LineChart data={data?.charts.sales_by_year ?? []}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eee" />
                  <XAxis dataKey="outlet_establishment_year" />
                  <YAxis tickFormatter={(value) => formatNumber(value)} />
                  <Tooltip formatter={(value) => typeof value === "number" ? formatCurrencyPrecise(value) : value} />
                  <Line type="monotone" dataKey="total_sales" stroke="#1d4ed8" strokeWidth={3} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
          <div className="rounded-3xl border border-black/10 bg-[color:var(--surface)] p-6 shadow-[0_18px_40px_rgba(0,0,0,0.08)]">
            <h2 className="text-lg font-semibold">Top Products</h2>
            <div className="mt-4 overflow-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-[color:var(--ink-muted)]">
                  <tr>
                    <th className="py-2">Product</th>
                    <th className="py-2">Category</th>
                    <th className="py-2">Total Sales</th>
                    <th className="py-2">Avg Rating</th>
                  </tr>
                </thead>
                <tbody>
                  {(data?.tables.top_products ?? []).map((row) => (
                    <tr key={row.item_identifier} className="border-t border-black/5">
                      <td className="py-2 font-medium text-[color:var(--foreground)]">{row.item_identifier}</td>
                      <td className="py-2 text-[color:var(--ink-muted)]">{row.item_type}</td>
                      <td className="py-2">{formatCurrencyPrecise(row.total_sales)}</td>
                      <td className="py-2">{row.avg_rating.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-3xl border border-black/10 bg-[color:var(--surface)] p-6 shadow-[0_18px_40px_rgba(0,0,0,0.08)]">
            <h2 className="text-lg font-semibold">Auto Predictions</h2>
            <p className="mt-2 text-sm text-[color:var(--ink-muted)]">
              Live model scoring across the filtered dataset.
            </p>
            <div className="mt-5 grid gap-4">
              <div className="rounded-2xl border border-black/10 bg-[color:var(--surface-muted)] p-4">
                <div className="text-xs uppercase tracking-[0.3em] text-[color:var(--ink-muted)]">Avg Predicted</div>
                <div className="mt-2 text-2xl font-semibold">
                  {predictionsSummary ? formatCurrencyPrecise(predictionsSummary.avg) : "-"}
                </div>
              </div>
              <div className="rounded-2xl border border-black/10 bg-[color:var(--surface-muted)] p-4">
                <div className="text-xs uppercase tracking-[0.3em] text-[color:var(--ink-muted)]">Total Predicted</div>
                <div className="mt-2 text-2xl font-semibold">
                  {predictionsSummary ? formatCurrency(predictionsSummary.total) : "-"}
                </div>
              </div>
              <div className="rounded-2xl border border-black/10 bg-[color:var(--surface-muted)] p-4 text-xs text-[color:var(--ink-muted)]">
                {data?.predictions.rows?.length ?? 0} rows scored
              </div>
            </div>
          </div>
        </section>

        <section className="rounded-3xl border border-black/10 bg-[color:var(--surface)] p-6 shadow-[0_18px_40px_rgba(0,0,0,0.08)]">
          <h2 className="text-lg font-semibold">Prediction Sample</h2>
          <div className="mt-4 overflow-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-[color:var(--ink-muted)]">
                <tr>
                  <th className="py-2">Item Type</th>
                  <th className="py-2">Outlet Type</th>
                  <th className="py-2">Sales</th>
                  <th className="py-2">Predicted</th>
                </tr>
              </thead>
              <tbody>
                {(data?.predictions.rows ?? []).slice(0, 8).map((row, index) => (
                  <tr key={index} className="border-t border-black/5">
                    <td className="py-2 font-medium">{String(row.item_type ?? "-")}</td>
                    <td className="py-2 text-[color:var(--ink-muted)]">{String(row.outlet_type ?? "-")}</td>
                    <td className="py-2">{row.total_sales ? formatCurrencyPrecise(Number(row.total_sales)) : "-"}</td>
                    <td className="py-2">
                      {row.predicted_total_sales ? formatCurrencyPrecise(Number(row.predicted_total_sales)) : "-"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {loading && <div className="text-sm text-[color:var(--ink-muted)]">Refreshing data...</div>}
        {error && <div className="text-sm text-red-600">{error}</div>}
      </main>
    </div>
  );
}
