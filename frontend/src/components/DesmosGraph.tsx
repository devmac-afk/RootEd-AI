import React, { useEffect, useRef } from 'react';

interface DesmosGraphProps {
  equations: string | string[];
}

declare global {
  interface Window {
    Desmos: any;
  }
}

const DesmosGraph: React.FC<DesmosGraphProps> = ({ equations }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const calculatorRef = useRef<any>(null);

  useEffect(() => {
    const scriptId = 'desmos-api-script';
    let script = document.getElementById(scriptId) as HTMLScriptElement;

    const initCalculator = () => {
      if (containerRef.current && !calculatorRef.current) {
        calculatorRef.current = window.Desmos.GraphingCalculator(containerRef.current);
      }
      updateEquations();
    };

    const updateEquations = () => {
      if (calculatorRef.current) {
        calculatorRef.current.setBlank();
        const eqs = Array.isArray(equations) ? equations : [equations];
        eqs.forEach((eq, index) => {
          if (eq) {
            calculatorRef.current.setExpression({ id: `graph${index}`, latex: eq });
          }
        });
      }
    };

    if (!script) {
      script = document.createElement('script');
      script.id = scriptId;
      script.src = 'https://www.desmos.com/api/v1.11/calculator.js?apiKey=dcb31709b452b1cf9dc26972add0fda6';
      script.async = true;
      script.onload = initCalculator;
      document.head.appendChild(script);
    } else if (window.Desmos) {
      initCalculator();
    }

    return () => {
      // We don't necessarily want to remove the script, but we could destroy the calculator instance if needed
    };
  }, [equations]);

  return (
    <div 
      ref={containerRef} 
      className="w-full h-[500px] border border-border rounded-md mt-4"
    />
  );
};

export default DesmosGraph;
