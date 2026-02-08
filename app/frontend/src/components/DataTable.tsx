import { useState } from 'react';

interface DataPoint {
  x: number;
  y: number;
}

interface DataTableProps {
  data: DataPoint[];
}

function DataTable({ data }: DataTableProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="expander">
      <div
        className="expander-header"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <span>{isExpanded ? '▼' : '▶'}</span>
        <span>Show time-series data</span>
      </div>
      {isExpanded && (
        <div className="expander-content">
          <table className="data-table">
            <thead>
              <tr>
                <th>#</th>
                <th>x</th>
                <th>y</th>
              </tr>
            </thead>
            <tbody>
              {data.map((point, index) => (
                <tr key={index}>
                  <td>{index + 1}</td>
                  <td>{point.x.toFixed(4)}</td>
                  <td>{point.y.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default DataTable;
