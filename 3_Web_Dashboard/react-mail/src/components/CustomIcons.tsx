import logo from '../assets/logo.png';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

export function EtcFriendsIcon() {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <img src={logo} alt="etc/friends" style={{ height: 58 }} />
      <Typography
        sx={{
          fontFamily: 'monospace',
          fontWeight: 700,
          color: '#00ff41',  // 터미널 초록색
          fontSize: '1rem',
          letterSpacing: '-0.02em',
        }}
      >
        /etc/friends
      </Typography>
    </Box>
  );
}