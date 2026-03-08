import { ReferenceArea, ReferenceLine } from 'recharts';
import type { ReactElement } from 'react';

export interface AnomalyEvent {
  /** Start of the anomaly region on the x-axis */
  x1: number;
  /** End of the anomaly region on the x-axis */
  x2: number;
  /** Label displayed on the shaded area (default: "Anomaly") */
  label?: string;
  /** Fill color for the shaded region (default: transparent red) */
  fill?: string;
  /** Stroke color for the boundary lines (default: #cc3333) */
  stroke?: string;
}

/**
 * Returns flat array of Recharts elements (ReferenceArea + two ReferenceLines)
 * that can be spread directly into a LineChart's children.
 * Recharts requires direct children — fragments break its child type inspection.
 */
export function renderAnomalyAreas(anomalies: AnomalyEvent[]): ReactElement[] {
  return anomalies.flatMap((event, i) => {
    const {
      x1,
      x2,
      label = 'Anomaly',
      fill = 'rgba(255, 0, 0, 0.1)',
      stroke = '#cc3333',
    } = event;

    return [
      <ReferenceArea
        key={`anomaly-area-${i}`}
        x1={x1}
        x2={x2}
        fill={fill}
        label={{ value: label, position: 'top', offset: 8, fill: stroke, fontSize: 12, fontWeight: 600 }}
      />,
      <ReferenceLine
        key={`anomaly-line-start-${i}`}
        x={x1}
        stroke={stroke}
        strokeDasharray="6 4"
        strokeWidth={1.5}
      />,
      <ReferenceLine
        key={`anomaly-line-end-${i}`}
        x={x2}
        stroke={stroke}
        strokeDasharray="6 4"
        strokeWidth={1.5}
      />,
    ];
  });
}
