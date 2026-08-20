interface ConfusionMatrixProps {
  matrix: number[][];
  labels?: string[];
}

export function ConfusionMatrix({ matrix, labels = [] }: ConfusionMatrixProps) {
  if (!matrix.length) return null;
  const resolvedLabels = labels.length === matrix.length
    ? labels
    : matrix.map((_, index) => String(index));

  return (
    <div className="confusion-matrix" style={{ overflowX: "auto" }}>
      <table>
        <caption>Confusion matrix</caption>
        <thead>
          <tr>
            <th aria-label="Actual and predicted labels" />
            {resolvedLabels.map((label) => <th key={`predicted-${label}`}>{label}</th>)}
          </tr>
        </thead>
        <tbody>
          {matrix.map((row, rowIndex) => (
            <tr key={resolvedLabels[rowIndex]}>
              <th scope="row">{resolvedLabels[rowIndex]}</th>
              {row.map((value, columnIndex) => (
                <td key={`${rowIndex}-${columnIndex}`}>{value}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
