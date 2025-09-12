import React from 'react'
import {
  ResponsiveContainer,
  BarChart, Bar,
  LineChart, Line,
  PieChart, Pie, Cell,
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend, AreaChart, Area
} from 'recharts'

const COLORS = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']

const Graphs = ({ spec }) => {
  if (!spec || !spec.type || !Array.isArray(spec.data) || spec.data.length === 0) return null
  const colors = spec.colors && spec.colors.length ? spec.colors : COLORS

  return (
    <div className='w-full rounded-lg border border-slate-200 bg-white p-4 shadow-sm'>
      {spec.title && <h3 className='text-slate-800 font-semibold mb-1'>{spec.title}</h3>}
      {spec.description && <p className='text-slate-500 text-sm mb-3'>{spec.description}</p>}
      <div className='w-full h-64'>
        <ResponsiveContainer width="100%" height="100%">
          {spec.type === 'bar' && (
            <BarChart data={spec.data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={spec.xKey} />
              <YAxis />
              <Tooltip />
              <Legend />
              {Array.isArray(spec.yKey) ? spec.yKey.map((k, idx) => (
                <Bar key={k} dataKey={k} fill={colors[idx % colors.length]} />
              )) : <Bar dataKey={spec.yKey} fill={colors[0]} />}
            </BarChart>
          )}
          {spec.type === 'line' && (
            <LineChart data={spec.data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={spec.xKey} />
              <YAxis />
              <Tooltip />
              <Legend />
              {Array.isArray(spec.yKey) ? spec.yKey.map((k, idx) => (
                <Line key={k} type="monotone" dataKey={k} stroke={colors[idx % colors.length]} dot={false} />
              )) : <Line type="monotone" dataKey={spec.yKey} stroke={colors[0]} dot={false} />}
            </LineChart>
          )}
          {spec.type === 'area' && (
            <AreaChart data={spec.data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={spec.xKey} />
              <YAxis />
              <Tooltip />
              <Legend />
              {Array.isArray(spec.yKey) ? spec.yKey.map((k, idx) => (
                <Area key={k} type="monotone" dataKey={k} stroke={colors[idx % colors.length]} fill={colors[idx % colors.length]} fillOpacity={0.2} />
              )) : <Area type="monotone" dataKey={spec.yKey} stroke={colors[0]} fill={colors[0]} fillOpacity={0.2} />}
            </AreaChart>
          )}
          {spec.type === 'scatter' && (
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey={spec.xKey} />
              <YAxis dataKey={Array.isArray(spec.yKey) ? spec.yKey[0] : spec.yKey} />
              <Tooltip />
              <Legend />
              <Scatter data={spec.data} fill={colors[0]} />
            </ScatterChart>
          )}
          {spec.type === 'pie' && (
            <PieChart>
              <Tooltip />
              <Legend />
              <Pie data={spec.data} dataKey={Array.isArray(spec.yKey) ? spec.yKey[0] : spec.yKey} nameKey={spec.xKey} outerRadius={110}>
                {spec.data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                ))}
              </Pie>
            </PieChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default Graphs
