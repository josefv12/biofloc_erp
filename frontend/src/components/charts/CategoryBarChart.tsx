import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatChartValue, formatNumber } from "../../utils/format";
import type { PuntoSerie } from "../../utils/series";
import type { LineaReferencia, SerieDefinicion } from "./TimeSeriesChart";

type CategoryBarChartProps = {
  data: PuntoSerie[];
  barras: SerieDefinicion[];
  lineas?: SerieDefinicion[];
  unidad?: string | null;
  referencias?: LineaReferencia[];
  digitos?: number;
  altura?: number;
};

const TICK = { fontSize: 11, fill: "var(--bf-muted)", fontFamily: "IBM Plex Sans, sans-serif" };

/** Barras por fecha, con líneas opcionales sobre el mismo eje (p. ej. acumulado). */
export function CategoryBarChart({
  data,
  barras,
  lineas = [],
  unidad,
  referencias = [],
  digitos = 0,
  altura = 280,
}: CategoryBarChartProps) {
  return (
    <div style={{ height: altura }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 10, right: 12, bottom: 4, left: 0 }} barCategoryGap="32%">
          <CartesianGrid stroke="var(--bf-border)" strokeOpacity={0.55} strokeDasharray="4 8" vertical={false} />
          <XAxis dataKey="etiqueta" tick={TICK} minTickGap={12} axisLine={false} tickLine={false} tickMargin={8} />
          <YAxis
            tick={TICK}
            width={56}
            axisLine={false}
            tickLine={false}
            tickMargin={6}
            tickFormatter={(valor) => formatNumber(valor, { maximumFractionDigits: digitos })}
          />
          <Tooltip
            cursor={{ fill: "var(--bf-accent-soft)" }}
            contentStyle={{
              borderRadius: 12,
              border: "1px solid var(--bf-border)",
              boxShadow: "0 8px 24px rgba(16,40,33,0.12)",
              fontSize: 12,
            }}
            formatter={(valor, nombre) => [
              formatChartValue(valor, { maximumFractionDigits: digitos }, unidad),
              nombre,
            ]}
          />
          {barras.length + lineas.length > 1 || referencias.length > 0 ? (
            <Legend wrapperStyle={{ fontSize: 11, color: "var(--bf-muted)" }} />
          ) : null}
          {referencias.map((referencia) => (
            <ReferenceLine
              key={referencia.etiqueta}
              y={referencia.valor}
              stroke={referencia.color ?? "#b45309"}
              strokeDasharray="5 4"
              label={{ value: referencia.etiqueta, position: "insideTopRight", fontSize: 10 }}
            />
          ))}
          {barras.map((serie) => (
            <Bar
              key={serie.key}
              dataKey={serie.key}
              name={serie.nombre}
              fill={serie.color ?? "var(--bf-accent)"}
              fillOpacity={0.88}
              radius={[6, 6, 2, 2]}
            />
          ))}
          {lineas.map((serie) => (
            <Line
              key={serie.key}
              type="monotone"
              dataKey={serie.key}
              name={serie.nombre}
              stroke={serie.color ?? "#1c4f43"}
              strokeWidth={2.5}
              strokeLinecap="round"
              dot={{ r: 4, stroke: "#fff", strokeWidth: 2 }}
              connectNulls={false}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
