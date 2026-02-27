import React, { useEffect, useState } from 'react';
import {
    Dialog, DialogTitle, DialogContent, DialogActions,
    Button, Typography, Box, Select, MenuItem, ToggleButtonGroup, ToggleButton
} from '@mui/material';
import TimelineIcon from '@mui/icons-material/Timeline';
import {
    LineChart, Line, XAxis, YAxis, CartesianGrid,
    Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import { api } from '../api';

export default function ChartDialog({ open, onClose }) {
    const isKiosk = new URLSearchParams(window.location.search).get("kiosk") === "true";

    const [range, setRange] = useState('1h');
    const [chartData, setChartData] = useState([]);
    const [chartType, setChartType] = useState('temperature'); // 'temperature' or 'dew_point'

    useEffect(() => {
        let interval;
        const fetchData = () => {
            api.getHistory(range)
                .then(response => {
                    const transformed = response.data.history.map(entry => ({
                        time: entry.timestamp.slice(11),
                        temperature: entry.temperature,
                        dew_point: entry.dew_point,
                        tempMin: entry.temp_min,
                        tempMax: entry.temp_max,
                        humMin: entry.hum_min,
                        humMax: entry.hum_max,
                    }));
                    setChartData(transformed);
                })
                .catch(error => {
                    console.error('Failed to fetch chart data:', error);
                    setChartData([]);
                });
        };

        if (open) {
            fetchData();

            const intervalTime = range === '1m' ? 1000 : range === '1h' ? 60000 : null;

            if (intervalTime) {
                interval = setInterval(fetchData, intervalTime);
            }
        }

        return () => {
            if (interval) clearInterval(interval);
        };
    }, [range, open]);

    return (
        <Dialog open={open} onClose={onClose} fullWidth maxWidth="md">
            <DialogTitle>
                <Box display="flex" alignItems="center">
                    <TimelineIcon sx={{ mr: 1 }} />
                    History
                </Box>
            </DialogTitle>
            <DialogContent dividers>
                <Box mb={2}>
                    <ToggleButtonGroup
                        value={chartType}
                        exclusive
                        onChange={(e, value) => { if (value) setChartType(value); }}
                        size="small"
                        aria-label="chart type"
                        sx={{ flexShrink: 0 }}
                    >
                        {/* <ToggleButton value="temperature" aria-label="temperature chart">
                            Temperature
                        </ToggleButton>
                        <ToggleButton value="dew_point" aria-label="dew_point chart">
                            dew point
                        </ToggleButton> */}
                    </ToggleButtonGroup>
                </Box>

                {chartType === 'temperature' && (
                    <Box width="100%" height={isKiosk ? 208 : 300}>
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={chartData} >
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="time" />
                                <YAxis
                                    domain={[0, 100]}
                                    tickFormatter={(value) => `${value}°C`}
                                />
                                <Tooltip />
                                <Legend />
                                <Line type="monotone" name="C°" dataKey="temperature" stroke="#ff5722" dot={false} isAnimationActive={false} />
                                {/* <Line type="monotone" name="Min" dataKey="tempMin" stroke="#ffccbc" strokeDasharray="5 5" dot={false} isAnimationActive={false} />
                                <Line type="monotone" name="Max" dataKey="tempMax" stroke="#bf360c" strokeDasharray="5 5" dot={false} isAnimationActive={false} /> */}
                            </LineChart>
                        </ResponsiveContainer>
                    </Box>
                )}

                {chartType === 'dew_point' && (
                    <Box width="100%" height={isKiosk ? 208 : 300}>
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={chartData}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="time" />
                                <YAxis
                                    width={100} tickFormatter={(value) => `${value}C°`}
                                />
                                <Tooltip />
                                <Legend />
                                <Line type="monotone" name="--" dataKey="dew_point" stroke="#2196f3" dot={false} isAnimationActive={false} />
                                {/* <Line type="monotone" name="Min" dataKey="humMin" stroke="#bbdefb" strokeDasharray="5 5" dot={false} isAnimationActive={false} />
                                <Line type="monotone" name="Max" dataKey="humMax" stroke="#0d47a1" strokeDasharray="5 5" dot={false} isAnimationActive={false} /> */}
                            </LineChart>
                        </ResponsiveContainer>
                    </Box>
                )}
            </DialogContent>
            <DialogActions sx={{ justifyContent: 'space-between', px: 2 }}>
                <Select
                    value={range}
                    onChange={(e) => setRange(e.target.value)}
                    size="small"
                    sx={{ minWidth: 160 }}
                >
                    <MenuItem value="1m">Last minute (1 value per second)</MenuItem>
                    <MenuItem value="1h">Last hour (1 value per minute)</MenuItem>
                    <MenuItem value="12h">12 hours (2 values per hour)</MenuItem>
                </Select>
                <Button onClick={onClose}>Close</Button>
            </DialogActions>
        </Dialog>
    );
}
