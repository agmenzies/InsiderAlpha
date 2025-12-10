"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import axios from "axios";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

export default function Dashboard() {
  const router = useRouter();
  const [leaderboard, setLeaderboard] = useState<any[]>([]);
  const [portfolio, setPortfolio] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [ticker, setTicker] = useState("");
  const [cost, setCost] = useState("");

  useEffect(() => {
    fetchLeaderboard();
  }, []);

  const fetchLeaderboard = async () => {
    try {
      const res = await axios.get("/api/leaderboard");
      setLeaderboard(res.data);
      setLoading(false);
    } catch (error: any) {
      console.error("Failed to fetch leaderboard", error);
      setLoading(false);
    }
  };

  const addToPortfolio = (e: any) => {
    e.preventDefault();
    setPortfolio([...portfolio, { ticker, cost, id: Date.now() }]);
    setTicker("");
    setCost("");
  };

  const data = [
    { name: 'Jan', Portfolio: 4000, SPY: 2400, Insider: 2400 },
    { name: 'Feb', Portfolio: 3000, SPY: 1398, Insider: 2210 },
    { name: 'Mar', Portfolio: 2000, SPY: 9800, Insider: 2290 },
    { name: 'Apr', Portfolio: 2780, SPY: 3908, Insider: 2000 },
    { name: 'May', Portfolio: 1890, SPY: 4800, Insider: 2181 },
  ];

  if (loading) return <div className="p-10 text-neon">LOADING DATA...</div>;

  return (
    <div className="min-h-screen bg-[#111] text-white p-8 font-sans">
      <header className="mb-12 border-b border-[#333] pb-4 flex justify-between items-center">
        <h1 className="text-4xl tracking-tighter">INSIDER<span className="text-neon">ALPHA</span></h1>
        <div className="text-sm text-gray-400">OFF TRACK METRICS</div>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Leaderboard Section */}
        <div className="col-span-2 bg-[#1a1a1a] p-6 border border-[#333]">
          <h2 className="text-2xl mb-6 text-neon border-l-4 border-neon pl-4">Insider Leaderboard</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-[#333] text-gray-400">
                  <th className="px-4 py-3 text-left">INSIDER</th>
                  <th className="px-4 py-3 text-left">COMPANY</th>
                  <th className="px-4 py-3 text-right text-neon">SCORE</th>
                  <th className="px-4 py-3 text-right">WIN RATE</th>
                  <th className="px-4 py-3 text-right">30D ALPHA</th>
                  <th className="px-4 py-3 text-right">BUY EFF (180D)</th>
                  <th className="px-4 py-3 text-right">SELL EFF (180D)</th>
                  <th className="px-4 py-3 text-right">1Y ALPHA</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard.length === 0 ? (
                  <tr><td colSpan={8} className="text-center py-8 text-gray-500">NO DATA AVAILABLE</td></tr>
                ) : (
                  leaderboard.map((insider) => (
                    <tr key={insider.cik} className="border-b border-[#333] hover:bg-[#222]">
                      <td className="px-4 py-3 font-bold">{insider.name}</td>
                      <td className="px-4 py-3 text-gray-400">{insider.company}</td>
                      <td className="px-4 py-3 text-right text-neon font-bold text-lg">{insider.score.toFixed(1)}</td>
                      <td className="px-4 py-3 text-right">
                        {Math.round((insider.wins / insider.total_trades) * 100)}%
                        <span className="text-xs text-gray-500 block">({insider.wins}/{insider.total_trades})</span>
                      </td>
                      <td className="px-4 py-3 text-right">{(insider.alpha_30d * 100).toFixed(1)}%</td>
                      <td className="px-4 py-3 text-right text-green-400">
                        {insider.total_buys > 0 ? (insider.buy_alpha_180d * 100).toFixed(1) + "%" : "-"}
                      </td>
                      <td className="px-4 py-3 text-right text-red-400">
                        {insider.total_sells > 0 ? (insider.sell_alpha_180d * 100).toFixed(1) + "%" : "-"}
                      </td>
                      <td className="px-4 py-3 text-right">{(insider.alpha_1y * 100).toFixed(1)}%</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Portfolio Section */}
        <div className="bg-[#1a1a1a] p-6 border border-[#333]">
          <h2 className="text-2xl mb-6 text-neon border-l-4 border-neon pl-4">My Portfolio</h2>
          <form onSubmit={addToPortfolio} className="flex flex-col gap-4 mb-8">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="TICKER"
                value={ticker}
                onChange={(e) => setTicker(e.target.value)}
                className="bg-[#222] border border-[#444] p-3 text-white w-full focus:outline-none focus:border-neon"
                required
              />
              <input
                type="number"
                placeholder="COST"
                value={cost}
                onChange={(e) => setCost(e.target.value)}
                className="bg-[#222] border border-[#444] p-3 text-white w-full focus:outline-none focus:border-neon"
                required
              />
            </div>
            <button type="submit" className="bg-neon text-black font-bold py-3 hover:opacity-90 transition-opacity">
              ADD POSITION
            </button>
          </form>
          <ul>
            {portfolio.map((item) => (
              <li key={item.id} className="border-b border-[#333] py-3 flex justify-between items-center">
                <span className="font-bold text-lg">{item.ticker}</span>
                <span className="text-gray-400">${item.cost}</span>
              </li>
            ))}
          </ul>
        </div>

      </div>

      {/* Chart Section */}
      <div className="mt-8 bg-[#1a1a1a] p-6 border border-[#333]">
        <h2 className="text-2xl mb-6 text-neon border-l-4 border-neon pl-4">Performance Comparison</h2>
        <div className="h-96">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="name" stroke="#666" />
              <YAxis stroke="#666" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#111', border: '1px solid #333' }}
                itemStyle={{ color: '#fff' }}
              />
              <Legend />
              <Line type="monotone" dataKey="Portfolio" stroke="#dfff00" strokeWidth={3} dot={{ r: 6, fill: '#dfff00' }} />
              <Line type="monotone" dataKey="SPY" stroke="#666" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="Insider" stroke="#fff" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
