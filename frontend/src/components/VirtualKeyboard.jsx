import React, { useEffect, useMemo, useState } from 'react';
import { useKeyboard } from '../KeyboardContext';

const KEYBOARD_CONTAINER_STYLE = {
  position: 'fixed',
  left: 0,
  right: 0,
  bottom: 0,
  background: '#e7e7e7',
  borderTop: '1px solid #cfcfcf',
  boxShadow: '0 -4px 14px rgba(0,0,0,0.22)',
  zIndex: 9999,
  padding: '10px 8px 12px',
};

const ROW_STYLE = {
  display: 'grid',
  gap: 6,
  marginBottom: 6,
};

const KEY_STYLE = {
  minHeight: 46,
  border: '1px solid #bcbcbc',
  borderRadius: 8,
  background: '#ffffff',
  fontSize: 19,
  fontWeight: 600,
  color: '#222',
};

const SPECIAL_KEY_STYLE = {
  ...KEY_STYLE,
  background: '#d8d8d8',
};

const WIDE_KEY_STYLE = {
  ...SPECIAL_KEY_STYLE,
  minWidth: 78,
};

const BASE_LAYOUT = {
  letters: [
    ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p'],
    ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l'],
    ['z', 'x', 'c', 'v', 'b', 'n', 'm'],
  ],
  symbols: [
    ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0'],
    ['!', '@', '#', '$', '%', '&', '/', '(', ')', '='],
    ['?', '+', '-', '_', ':', ';', ',', '.', '"'],
  ],
};

const NUMERIC_LAYOUT = [
  ['1', '2', '3'],
  ['4', '5', '6'],
  ['7', '8', '9'],
  ['.', '0'],
];

function normalizeType(type) {
  if (type === 'numeric') return 'numeric';
  return 'text';
}

function normalizeValue(value) {
  if (value === null || value === undefined) return '';
  return String(value);
}

export default function VirtualKeyboard() {
  const {
    isOpen,
    currentValue,
    keyboardType,
    updateValue,
    closeKeyboard,
    onSubmitCallback,
  } = useKeyboard();

  const [value, setValue] = useState('');
  const [isShift, setIsShift] = useState(false);
  const [isSymbols, setIsSymbols] = useState(false);

  const inputType = normalizeType(keyboardType);

  useEffect(() => {
    if (!isOpen) return;

    setValue(normalizeValue(currentValue));
    setIsShift(false);
    setIsSymbols(false);
  }, [isOpen, currentValue]);

  const setInputValue = (nextValue) => {
    const normalized = normalizeValue(nextValue);
    setValue(normalized);
    updateValue?.(normalized);
  };

  const addCharacter = (char) => {
    const nextValue = `${normalizeValue(value)}${char}`;
    setInputValue(nextValue);
    if (isShift && inputType === 'text') {
      setIsShift(false);
    }
  };

  const handleAction = (action) => {
    if (action === 'bksp') {
      setInputValue(normalizeValue(value).slice(0, -1));
      return;
    }

    if (action === 'enter') {
      onSubmitCallback?.(normalizeValue(value));
      closeKeyboard();
      return;
    }

    if (action === 'space') {
      addCharacter(' ');
      return;
    }

    if (action === 'shift') {
      setIsShift((prev) => !prev);
      return;
    }

    if (action === 'symbols') {
      setIsSymbols((prev) => !prev);
      setIsShift(false);
      return;
    }

    if (action === 'clear') {
      setInputValue('');
    }
  };

  const rows = useMemo(() => {
    if (inputType === 'numeric') return NUMERIC_LAYOUT;
    const base = isSymbols ? BASE_LAYOUT.symbols : BASE_LAYOUT.letters;

    if (!isShift || isSymbols) return base;

    return base.map((row) => row.map((k) => k.toUpperCase()));
  }, [inputType, isShift, isSymbols]);

  if (!isOpen) return null;

  return (
    <>
      <div
        role="button"
        tabIndex={-1}
        onClick={closeKeyboard}
        onKeyDown={() => {}}
        style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0,0,0,0.45)',
          zIndex: 9998,
        }}
      />

      <div style={KEYBOARD_CONTAINER_STYLE} onClick={(e) => e.stopPropagation()}>
        <div
          style={{
            background: '#fff',
            border: '1px solid #cecece',
            borderRadius: 8,
            minHeight: 46,
            marginBottom: 8,
            padding: '10px 12px',
            fontSize: 20,
            overflowX: 'auto',
            whiteSpace: 'nowrap',
          }}
        >
          {value || <span style={{ color: '#9e9e9e' }}>Scrivi qui…</span>}
        </div>

        {rows.map((row, rowIndex) => (
          <div
            key={`row-${rowIndex}`}
            style={{
              ...ROW_STYLE,
              gridTemplateColumns: `repeat(${row.length}, minmax(0, 1fr))`,
            }}
          >
            {row.map((key) => (
              <button
                key={key}
                type="button"
                style={KEY_STYLE}
                onClick={() => addCharacter(key)}
              >
                {key}
              </button>
            ))}
          </div>
        ))}

        {inputType === 'text' && (
          <div style={{ ...ROW_STYLE, gridTemplateColumns: '1fr 2fr 1fr 1fr' }}>
            <button type="button" style={WIDE_KEY_STYLE} onClick={() => handleAction('shift')}>
              {isShift ? '⇧ ON' : '⇧'}
            </button>
            <button type="button" style={WIDE_KEY_STYLE} onClick={() => handleAction('space')}>
              spazio
            </button>
            <button type="button" style={WIDE_KEY_STYLE} onClick={() => handleAction('symbols')}>
              {isSymbols ? 'ABC' : '#+='}
            </button>
            <button type="button" style={WIDE_KEY_STYLE} onClick={() => handleAction('bksp')}>
              ⌫
            </button>
          </div>
        )}

        {inputType === 'numeric' && (
          <div style={{ ...ROW_STYLE, gridTemplateColumns: '1fr 1fr' }}>
            <button type="button" style={WIDE_KEY_STYLE} onClick={() => handleAction('clear')}>
              Pulisci
            </button>
            <button type="button" style={WIDE_KEY_STYLE} onClick={() => handleAction('bksp')}>
              ⌫
            </button>
          </div>
        )}

        <div style={{ ...ROW_STYLE, gridTemplateColumns: '1fr 1fr' }}>
          <button type="button" style={SPECIAL_KEY_STYLE} onClick={closeKeyboard}>
            Chiudi
          </button>
          <button
            type="button"
            style={{ ...SPECIAL_KEY_STYLE, background: '#89d482', borderColor: '#71bf6b' }}
            onClick={() => handleAction('enter')}
          >
            OK
          </button>
        </div>
      </div>
    </>
  );
}
