import { useEffect, useState, useRef } from 'react';
import { Box, Container } from '@mui/material';
import Header from './components/Header';
import StatusManager from './components/StatusManager';
import DateTimeDisplay from './components/DateTimeDisplay';
import BackButton from './components/BackButton';
import './App.css';
import { api } from './api';
import "react-simple-keyboard/build/css/index.css";
import { KeyboardProvider } from './KeyboardContext';
import VirtualKeyboard from './components/VirtualKeyboard';
import { SnackbarProvider } from 'notistack';

export default function App() {
  const [showBackButton, setShowBackButton] = useState(false);
  const [presetsVersion, setPresetsVersion] = useState(0);
  const handlePresetSaved = () => setPresetsVersion(v => v + 1);
  const isKiosk = new URLSearchParams(window.location.search).get("kiosk") === "true";

  useEffect(() => {
    const checkG1OS = async () => {
      const result = await api.getconnectionG1OS();
      setShowBackButton(result.data.status === true);
    };
    checkG1OS();
  }, []);

  useEffect(() => {
    if (isKiosk) {
      const meta = document.createElement("meta");
      meta.name = "viewport";
      meta.content = "width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no";
      document.head.appendChild(meta);
      return () => document.head.removeChild(meta);
    }
  }, [isKiosk]);

  useEffect(() => {
    if (isKiosk) {
      const preventZoom = (e) => {
        if (
          (e.ctrlKey && (e.key === '+' || e.key === '-' || e.key === '=')) ||
          e.key === "Meta"
        ) {
          e.preventDefault();
        }
      };
      const preventWheel = (e) => { if (e.ctrlKey) e.preventDefault(); };
      document.addEventListener("keydown", preventZoom, { passive: false });
      document.addEventListener("wheel", preventWheel, { passive: false });
      return () => {
        document.removeEventListener("keydown", preventZoom);
        document.removeEventListener("wheel", preventWheel);
      };
    }
  }, [isKiosk]);

  return (
    <SnackbarProvider maxSnack={15} autoHideDuration={null} anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}>
      <KeyboardProvider>
        {isKiosk && (
          <style>{`* { cursor: none !important; }`}</style>
        )}

        <Box
          sx={{
            backgroundColor: '#E0E0E0',
            minHeight: '90vh',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            position: 'relative',
          }}
        >
          <Container
            maxWidth="sm"
            sx={{
              backgroundColor: '#fff',
              color: '#333',
              borderRadius: 4,
              p: 3,
              boxShadow: 6,
              zIndex: 1,
            }}
          >
            <Header onPresetSaved={handlePresetSaved} />
            <StatusManager presetsVersion={presetsVersion} />
          </Container>

          {/* Logo cliccabile */}
          <Box
            component="img"
            src="/Logo_ginger.svg"
            alt="Logo Ginger"
            sx={{
              position: 'fixed',
              bottom: 16,
              right: 16,
              width: "8vw",
              maxWidth: 100,
              height: 'auto',
              opacity: 0.7,
              zIndex: 10,
            }}
          />

          {showBackButton && !isKiosk && (
            <BackButton onClick={() => window.location.href = 'https://g1os.local'} />
          )}

          <DateTimeDisplay />
        </Box>

        <VirtualKeyboard />

      </KeyboardProvider>
    </SnackbarProvider>
  );
}
