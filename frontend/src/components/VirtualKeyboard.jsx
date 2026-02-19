import React, { useRef, useEffect, useState } from 'react';
import Keyboard from 'react-simple-keyboard';
import { useKeyboard } from '../KeyboardContext';
import 'react-simple-keyboard/build/css/index.css';

export default function VirtualKeyboard() {
  const {
    isOpen,
    currentValue,
    keyboardType,
    updateValue,
    closeKeyboard,
    onSubmitCallback
  } = useKeyboard();

  const keyboardRef = useRef();
  const [localValue, setLocalValue] = useState(currentValue);
  const [layoutName, setLayoutName] = useState('default');

  const numericLayout = {
    default: [
      '1 2 3',
      '4 5 6',
      '7 8 9',
      '0 . {bksp}',
      '{enter}'
    ]
  };

  // Layout modificato per Android style e pulito
  const androidStyleLayouts = {
    default: [
      '1 2 3 4 5 6 7 8 9 0',
      'q w e r t y u i o p',
      'a s d f g h j k l ì',
      '{lock} z x c v b n m {bksp}',
      '{symbols} {space} {enter}'
    ],
    shift: [
      '! " # $ % & / ( ) =',
      'Q W E R T Y U I O P',
      'A S D F G H J K L °',
      '{lock} Z X C V B N M {bksp}',
      '{symbols} {space} {enter}'
    ],
    symbols: [
      '1 2 3 4 5 6 7 8 9 0',
      '[ ] { } # % ^ * + =',
      '_ \\ | ~ < > $ € £ ¥',
      ': ; , . ? ! \' " {bksp}',
      '{abc} {space} {enter}'
    ]
  };

  useEffect(() => {
    setLocalValue(currentValue);
    if (keyboardRef.current) {
      keyboardRef.current.setInput(currentValue);
    }
  }, [currentValue]);

  const handleChange = input => {
    setLocalValue(input);
    updateValue?.(input);
  };

  const handleKeyPress = button => {
    if (button === '{enter}') {
      onSubmitCallback(localValue);
      setTimeout(function () { closeKeyboard(); }, 200);
    }

    if (button === '{bksp}') {
      const newVal = localValue.slice(0, -1);
      setLocalValue(newVal);
      keyboardRef.current.setInput(newVal);
      updateValue?.(newVal);
    }

    if (button === '{lock}') {
      const nextLayout = layoutName === 'default' ? 'shift' : 'default';
      setLayoutName(nextLayout);
    }

    if (button === '{symbols}') {
      setLayoutName('symbols');
    }

    if (button === '{abc}') {
      setLayoutName('default');
    }
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop cliccabile per chiudere la tastiera */}
      <div
        onClick={closeKeyboard}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.4)',
          zIndex: 9998,
        }}
      />

      {/* Container tastiera */}
      <div
        style={{
          position: 'fixed',
          bottom: 0,
          left: 0,
          right: 0,
          background: '#E0E0E0',
          zIndex: 9999,
          borderTop: '1px solid #ccc',
          padding: '12px 8px 8px',
          boxShadow: '0 -2px 8px rgba(0,0,0,0.2)',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Preview del valore */}
        <div
          style={{
            marginBottom: '8px',
            padding: '8px',
            background: '#ffffff',
            border: '1px solid #ccc',
            borderRadius: '4px',
            fontSize: '18px',
            minHeight: '21px',
            overflowX: 'auto',
          }}
        >
          {localValue || <span style={{ color: '#aaa' }}>Type here...</span>}
        </div>

        <Keyboard
          keyboardRef={r => (keyboardRef.current = r)}
          onChange={handleChange}
          onKeyPress={handleKeyPress}
          layoutName={layoutName}
          layout={keyboardType === 'numeric' ? numericLayout : androidStyleLayouts}
          display={{
            '{bksp}': '⌫',
            '{enter}': 'OK',
            '{space}': '␣',
            '{lock}': '⇪',
            '{symbols}': '#+=',
            '{abc}': 'ABC',
          }}
        />
      </div>
    </>
  );
}
