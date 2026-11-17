import { usePlanPredictions } from '@/queries/dispatcher/usePlanPredictions'
import { Button } from '@/components/atoms/button'
import { Panel, Notice } from '@/components/molecules/Common'

export function PlanPredictionPanel() {
  const predictions = usePlanPredictions()
  if (!predictions.available) return null
  return (
    <Panel title="Estimated handling and late-arrival risk">
      <div className="panel-body">
        <p className="mb-3">
          Estimate the saved plan using planned inputs. Review these estimates alongside delivery
          windows and capacity checks.
        </p>
        <Button onClick={() => predictions.mutate()} disabled={predictions.isPending}>
          {predictions.isPending ? 'Estimating…' : 'Estimate saved plan'}
        </Button>
        {predictions.isError && (
          <Notice tone="warning" title="Estimates unavailable">
            {predictions.error.message}
          </Notice>
        )}
        {predictions.data && (
          <>
            <p className="my-3 text-sm">
              Model {predictions.data.model_version} · {predictions.data.predictions.length} orders.
              Refresh estimates after changing the plan.
            </p>
            <div className="overflow-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Order</th>
                    <th>Handling</th>
                    <th>Late-arrival probability</th>
                  </tr>
                </thead>
                <tbody>
                  {predictions.data.predictions.map((row) => (
                    <tr key={row.delivery_id}>
                      <td>{row.delivery_id}</td>
                      <td>{row.pred_service_min.toFixed(1)} min</td>
                      <td>{(row.pred_late_prob * 100).toFixed(1)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </div>
    </Panel>
  )
}
