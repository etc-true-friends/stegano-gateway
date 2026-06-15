import * as React from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import type { SvgIconProps } from '@mui/material/SvgIcon';

const materialTheme = createTheme();

type MaterialIconProps = {
  children: React.ReactElement<SvgIconProps>;
};

/** Joy CssVarsProvider와 분리된 Material 테마 — SvgIcon 전용 */
export default function MaterialIcon({ children }: MaterialIconProps) {
  return (
    <ThemeProvider theme={materialTheme}>
      {React.cloneElement(children, {
        ...children.props,
        fontSize: children.props.fontSize ?? 'inherit',
      })}
    </ThemeProvider>
  );
}
