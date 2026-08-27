import React, { useEffect, useRef } from 'react';
import Plotly from 'plotly.js-dist-min';
import { useTheme } from '../hooks/useTheme';

interface PlotlyChartProps {
  data: Plotly.Data[];
  layout?: Partial<Plotly.Layout>;
  config?: Partial<Plotly.Config>;
  style?: React.CSSProperties;
  className?: string;
}

export const PlotlyChart: React.FC<PlotlyChartProps> = ({
  data,
  layout = {},
  config = {},
  style,
  className = 'w-full h-full min-h-[300px]',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { isDark } = useTheme();

  useEffect(() => {
    if (!containerRef.current) return;

    const baseLayout: Partial<Plotly.Layout> = {
      autosize: true,
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: {
        family: 'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        color: isDark ? '#c9d1d9' : '#24292f',
        size: 12,
      },
      margin: { l: 48, r: 24, t: 32, b: 40, pad: 4 },
      ...layout,
    };

    const baseConfig: Partial<Plotly.Config> = {
      responsive: true,
      displayModeBar: false, // Clean look, toggles done via UI
      ...config,
    };

    Plotly.react(containerRef.current, data, baseLayout, baseConfig);

    const resizeObserver = new ResizeObserver(() => {
      if (containerRef.current) {
        Plotly.Plots.resize(containerRef.current);
      }
    });

    resizeObserver.observe(containerRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, [data, layout, config, isDark]);

  return <div ref={containerRef} style={style} className={className} />;
};
