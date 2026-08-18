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

/** Barras por fecha, con líneas opcionales sobre el mismo eje (p. ej. acumulado). */
export function CategoryBarChart({
  data,
  barras,
  lineas = [],
  unidad,
  referencias = [],
  digitos = 0,
  altura = 240,
}: CategoryBarChartProps) {
  return (
    <div style={{ height: altura }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 12, bottom: 4, left: 0 }} barCategoryGap="28%">
          <CartesianGrid strokeDasharray="3 3" stroke="var(--bf-border)" vertical={false} />
          <XAxis dataKey="etiqueta" tick={{ fontSize: 11 }} minTickGap={12} />
          <YAxis
            tick={{ fontSize: 11 }}
            width={56}
            tickFormatter={(valor) => formatNumber(valor, { maximumFractionDigits: digitos })}
          />
          <Tooltip
            formatter={(valor, nombre) => [
              formatChartValue(valor, { maximumFractionDigits: digitos }, unidad),
              nombre,
            ]}
          />
          {barras.length + lineas.length > 1 || referencias.length > 0 ? (
            <Legend wrapperStyle={{ fontSize: 11 }} />
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
              radius={[4, 4, 0, 0]}
            />
          ))}
          {lineas.map((serie) => (
            <Line
              key={serie.key}
              type="monotone"
              dataKey={serie.key}
              name={serie.nombre}
              stroke={serie.color ?? "#1c4f43"}
              strokeWidth={2}
              dot={{ r: 3 }}
              connectNulls={false}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
