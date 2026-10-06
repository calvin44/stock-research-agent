'use client'

import { useEffect, useRef } from 'react'
import type { IChartApi } from 'lightweight-charts'
import { PriceHistory } from '@/app/lib/api'

interface PriceChartProps {
  data: PriceHistory[]
}

export default function PriceChart({ data }: PriceChartProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!containerRef.current || data.length === 0) return

    import('lightweight-charts').then(
      ({ createChart, ColorType, LineSeries }) => {
        if (chartRef.current) {
          chartRef.current.remove()
        }

        const chart = createChart(containerRef.current!, {
          layout: {
            background: { type: ColorType.Solid, color: '#141414' },
            textColor: '#555',
          },
          grid: {
            vertLines: { color: '#1e1e1e' },
            horzLines: { color: '#1e1e1e' },
          },
          crosshair: {
            vertLine: { color: '#2a2a2a' },
            horzLine: { color: '#2a2a2a' },
          },
          rightPriceScale: { borderColor: '#1e1e1e' },
          timeScale: {
            borderColor: '#1e1e1e',
            timeVisible: false,
          },
          height: 120,
        })

        const series = chart.addSeries(LineSeries, {
          color: '#5DCAA5',
          lineWidth: 2,
          priceLineVisible: false,
          lastValueVisible: true,
        })

        series.setData(
          data.map((d) => ({
            time: d.date,
            value: d.close,
          })),
        )

        chart.timeScale().fitContent()
        chartRef.current = chart
      },
    )

    return () => {
      if (chartRef.current) {
        chartRef.current.remove()
        chartRef.current = null
      }
    }
  }, [data])

  return (
    <div className="bg-[#141414] border border-[#1e1e1e] rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 border-b border-[#1e1e1e]">
        <p className="text-[10px] font-medium text-[#555] uppercase tracking-widest">
          Price · 30 days
        </p>
      </div>
      <div ref={containerRef} className="w-full" />
    </div>
  )
}
