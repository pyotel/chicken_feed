'use client'

import { useEffect, useState } from 'react'
import axios from 'axios'
import { format } from 'date-fns'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { Activity, AlertCircle, CheckCircle, XCircle } from 'lucide-react'

// Use window location for API URL to work in any environment
const getApiUrl = () => {
  if (typeof window !== 'undefined') {
    // Client-side: use same host but different port
    return `http://${window.location.hostname}:37211`
  }
  // Server-side: use environment variable
  return process.env.NEXT_PUBLIC_API_URL || 'http://ketiict.com:37211'
}

const API_URL = getApiUrl()
const DEVICE_ID = 'raspberry-pi-001' // Default device ID

interface FeedingLog {
  id: number
  device_id: string
  action: string
  timestamp: string
  details: any
}

interface DailyStat {
  date: string
  opens: number
  closes: number
  errors: number
  missed?: number
}

interface MissedFeeding {
  id: number
  scheduled_time: string
  detected_at: string
  resolved: boolean
}

export default function Dashboard() {
  const [logs, setLogs] = useState<FeedingLog[]>([])
  const [stats, setStats] = useState<DailyStat[]>([])
  const [missedFeedings, setMissedFeedings] = useState<MissedFeeding[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch logs
      const logsResponse = await axios.get(
        `${API_URL}/api/feeding/logs/${DEVICE_ID}?limit=50`
      )
      setLogs(logsResponse.data)

      // Fetch statistics
      const statsResponse = await axios.get(
        `${API_URL}/api/stats/${DEVICE_ID}?days=7`
      )

      // Combine feeding stats with missed feedings
      const combinedStats = statsResponse.data.feeding_stats.map((stat: any) => {
        const missedData = statsResponse.data.missed_feedings.find(
          (m: any) => m.date === stat.date
        )
        return {
          ...stat,
          missed: missedData?.missed_count || 0,
        }
      })
      setStats(combinedStats)

      // Fetch missed feedings for today
      const today = format(new Date(), 'yyyy-MM-dd')
      const missedResponse = await axios.get(
        `${API_URL}/api/feeding/missed/${DEVICE_ID}?date=${today}`
      )
      setMissedFeedings(missedResponse.data)

      setLastUpdate(new Date())
    } catch (err: any) {
      console.error('Error fetching data:', err)
      const errorMessage = err.response?.data?.error || err.message || 'Failed to fetch data from server'
      console.error('API URL:', API_URL)
      console.error('Error details:', {
        message: err.message,
        response: err.response,
        config: err.config
      })
      setError(errorMessage)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const getStatusBadge = (action: string) => {
    switch (action) {
      case 'open':
        return <Badge className="bg-green-500">열림</Badge>
      case 'close':
        return <Badge className="bg-blue-500">닫힘</Badge>
      case 'error':
        return <Badge variant="destructive">오류</Badge>
      case 'startup':
        return <Badge className="bg-yellow-500">시작</Badge>
      case 'shutdown':
        return <Badge className="bg-gray-500">종료</Badge>
      default:
        return <Badge>{action}</Badge>
    }
  }

  const recentStats = stats[0] || { opens: 0, closes: 0, errors: 0, missed: 0 }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold mb-2">닭 먹이 자동 급여 시스템 모니터링</h1>
          <p className="text-gray-600">
            장치 ID: {DEVICE_ID} | 마지막 업데이트: {format(lastUpdate, 'yyyy-MM-dd HH:mm:ss')}
          </p>
        </div>

        {error && (
          <Alert className="mb-4" variant="destructive">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">오늘 급여 횟수</CardTitle>
              <CheckCircle className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{recentStats.opens}</div>
              <p className="text-xs text-gray-500">정상 작동</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">놓친 급여</CardTitle>
              <XCircle className="h-4 w-4 text-red-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{recentStats.missed || 0}</div>
              <p className="text-xs text-gray-500">미실행</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">오류 발생</CardTitle>
              <AlertCircle className="h-4 w-4 text-yellow-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{recentStats.errors}</div>
              <p className="text-xs text-gray-500">오늘 발생</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">시스템 상태</CardTitle>
              <Activity className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {logs.length > 0 && logs[0].action === 'startup' ? '작동중' : '정상'}
              </div>
              <p className="text-xs text-gray-500">실시간 모니터링</p>
            </CardContent>
          </Card>
        </div>

        {/* Tabs for different views */}
        <Tabs defaultValue="logs" className="space-y-4">
          <TabsList>
            <TabsTrigger value="logs">실시간 로그</TabsTrigger>
            <TabsTrigger value="chart">통계 차트</TabsTrigger>
            <TabsTrigger value="missed">놓친 급여</TabsTrigger>
          </TabsList>

          <TabsContent value="logs" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>최근 급여 기록</CardTitle>
              </CardHeader>
              <CardContent>
                <Table>
                  <TableCaption>최근 50개 이벤트</TableCaption>
                  <TableHeader>
                    <TableRow>
                      <TableHead>시간</TableHead>
                      <TableHead>동작</TableHead>
                      <TableHead>상세</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {logs.map((log) => (
                      <TableRow key={log.id}>
                        <TableCell>
                          {format(new Date(log.timestamp), 'MM-dd HH:mm:ss')}
                        </TableCell>
                        <TableCell>{getStatusBadge(log.action)}</TableCell>
                        <TableCell className="text-sm text-gray-600">
                          {log.details && JSON.stringify(log.details)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="chart" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>주간 급여 통계</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={stats}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="opens" fill="#10b981" name="급여 횟수" />
                    <Bar dataKey="missed" fill="#ef4444" name="놓친 급여" />
                    <Bar dataKey="errors" fill="#f59e0b" name="오류" />
                  </BarChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>일일 작동 패턴</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={stats}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="opens"
                      stroke="#10b981"
                      name="열림"
                    />
                    <Line
                      type="monotone"
                      dataKey="closes"
                      stroke="#3b82f6"
                      name="닫힘"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="missed" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>놓친 급여 목록</CardTitle>
              </CardHeader>
              <CardContent>
                {missedFeedings.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    오늘 놓친 급여가 없습니다
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>예정 시간</TableHead>
                        <TableHead>감지 시간</TableHead>
                        <TableHead>상태</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {missedFeedings.map((missed) => (
                        <TableRow key={missed.id}>
                          <TableCell>
                            {format(
                              new Date(missed.scheduled_time),
                              'MM-dd HH:mm'
                            )}
                          </TableCell>
                          <TableCell>
                            {format(
                              new Date(missed.detected_at),
                              'MM-dd HH:mm:ss'
                            )}
                          </TableCell>
                          <TableCell>
                            {missed.resolved ? (
                              <Badge className="bg-green-500">해결됨</Badge>
                            ) : (
                              <Badge variant="destructive">미해결</Badge>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}