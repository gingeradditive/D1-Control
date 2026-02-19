import { Box, Typography } from "@mui/material";

function formatElapsed(totalSeconds) {
  const h = Math.floor(totalSeconds / 3600);
  const m = Math.floor((totalSeconds % 3600) / 60);
  const s = totalSeconds % 60;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

export default function TemperatureDisplay({ currentTemp, setpoint, status, dryingElapsedSeconds }) {
  // Colori condizionati dallo status
  const ringColor = status ? "#d72e28" : "#ccc";
  const animated = status;

  return (
    <Box textAlign="center" sx={{ height: "126px", marginBottom: "36px" }}>
      <Box
        sx={{
          width: 200,
          height: 200,
          position: "relative",
          margin: "auto",
          top: "-37px"
        }}
      >
        {/* Cerchi */}
        <Box
          sx={{
            position: "absolute",
            top: -2,
            left: -2,
            width: "calc(100% + 4px)",
            height: "calc(100% + 4px)",
            border: `1px dashed ${ringColor}`,
            borderRadius: "50%",
            animation: animated ? "pulse1 9s ease-in-out infinite" : "none",
          }}
        />
        <Box
          sx={{
            position: "absolute",
            top: 6,
            left: 6,
            width: 187,
            height: 187,
            border: `2px dotted ${ringColor}`,
            borderRadius: "50%",
            animation: animated ? "pulse2 6s ease-in-out infinite" : "none",
          }}
        />
        <Box
          sx={{
            position: "absolute",
            top: 14,
            left: 14,
            width: 172,
            height: 172,
            border: `2px solid ${ringColor}`,
            borderRadius: "50%",
            animation: animated ? "pulse3 3s ease-in-out infinite" : "none",
          }}
        />

        {/* Contenuto centrale */}
        <Box
          sx={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Typography variant="h2" pl={3} className="temperature-degree">
            {currentTemp !== null ? `${currentTemp}` : "--"}
          </Typography>
          <Typography variant="body2" color="gray" className="temperature-degree">
            Set {setpoint !== null ? `${setpoint}` : ""}
          </Typography>
          {status && dryingElapsedSeconds > 0 && (
            <Typography variant="caption" color="gray" sx={{ mt: 0.5, fontFamily: 'monospace' }}>
              {formatElapsed(dryingElapsedSeconds)}
            </Typography>
          )}
        </Box>
      </Box>

      {/* Animazioni CSS */}
      <style>{`
        @keyframes pulse1 {
          0%, 100% { transform: scale(1) rotate(0deg); }
          50% { transform: scale(1.05) rotate(10deg); }
        }
        @keyframes pulse2 {
          0%, 100% { transform: scale(1) rotate(0deg); }
          50% { transform: scale(1.03) rotate(-10deg); }
        }
        @keyframes pulse3 {
          0%, 100% { transform: scale(1);}
          50% { transform: scale(1.02); }
        }
        .temperature-degree::after {
          content: "°";
          font-size: 0.8em;
          vertical-align: baseline;
          position: relative;
          top: -0.2em;
        }
      `}</style>
    </Box>
  );
}
