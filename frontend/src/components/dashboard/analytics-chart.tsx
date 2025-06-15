'use client'

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts'

const apiUsageData = [
  { name: 'Mon', calls: 4000, errors: 24 },
  { name: 'Tue', calls: 3000, errors: 13 },
  { name: 'Wed', calls: 2000, errors: 8 },
  { name: 'Thu', calls: 2780, errors: 15 },
  { name: 'Fri', calls: 1890, errors: 5 },
  { name: 'Sat', calls: 2390, errors: 10 },
  { name: 'Sun', calls: 3490, errors: 18 }
]

const endpointData = [
  { name: '/api/users', value: 35, color: '#3b82f6' },
  { name: '/api/auth', value: 25, color: '#8b5cf6' },
  { name: '/api/data', value: 20, color: '#06b6d4' },
  { name: '/api/files', value: 12, color: '#10b981' },
  { name: 'Others', value: 8, color: '#f59e0b' }
]

export function UsageChart() {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={apiUsageData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Bar dataKey="calls" fill="#3b82f6" radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export function ErrorChart() {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={apiUsageData}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip />
        <Line 
          type="monotone" 
          dataKey="errors" 
          stroke="#ef4444" 
          strokeWidth={2}
          dot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

export function EndpointChart() {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={endpointData}
          cx="50%"
          cy="50%"
          outerRadius={80}
          dataKey="value"
          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
        >
          {endpointData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip />
      </PieChart>
    </ResponsiveContainer>
  )
}