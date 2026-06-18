import * as React from 'react';
import GlobalStyles from '@mui/joy/GlobalStyles';
import Avatar from '@mui/joy/Avatar';
import Box from '@mui/joy/Box';
import Chip from '@mui/joy/Chip';
import Divider from '@mui/joy/Divider';
import IconButton from '@mui/joy/IconButton';
import List from '@mui/joy/List';
import ListItem from '@mui/joy/ListItem';
import ListItemButton, { listItemButtonClasses } from '@mui/joy/ListItemButton';
import ListItemContent from '@mui/joy/ListItemContent';
import Typography from '@mui/joy/Typography';
import Sheet from '@mui/joy/Sheet';
import Tooltip from '@mui/joy/Tooltip';
import { useColorScheme } from '@mui/joy/styles';
import DarkModeRoundedIcon from '@mui/icons-material/DarkModeRounded';
import InboxRoundedIcon from '@mui/icons-material/InboxRounded';
import LightModeRoundedIcon from '@mui/icons-material/LightModeRounded';
import SendRoundedIcon from '@mui/icons-material/SendRounded';
import LogoutRoundedIcon from '@mui/icons-material/LogoutRounded';
import { useNavigate, useLocation } from 'react-router-dom';
import logo from '../../assets/logo.png';
import MaterialIcon from './MaterialIcon';
import { fetchInboxCount } from '../../api/mailbox';
import { clearAuthSession, getStoredAuthUser } from '../../api/auth';

export default function Navigation() {
  const navigate = useNavigate();
  const location = useLocation();
  const { mode, systemMode, setMode } = useColorScheme();
  const [inboxCount, setInboxCount] = React.useState(0);
  const resolvedMode = mode === 'system' ? systemMode : mode;
  const isDarkMode = resolvedMode === 'dark';

  const handleLogout = () => {
    clearAuthSession();
    navigate('/login', { replace: true });
  };

  React.useEffect(() => {
    const load = async () => {
      const user = getStoredAuthUser();
      const email = user?.email ?? 'admin@gmail.com';
      try {
        const res = await fetchInboxCount(email);
        setInboxCount(res.inboxCount);
      } catch {
        // Keep the current count when the API request fails.
      }
    };
    load();
  }, []);

  React.useEffect(() => {
    const handleInboxRead = () => {
      setInboxCount((count) => Math.max(0, count - 1));
    };

    window.addEventListener('mailbox:inbox-read', handleInboxRead);
    return () => window.removeEventListener('mailbox:inbox-read', handleInboxRead);
  }, []);

  return (
    <Sheet
      className="Navigation"
      sx={{
        position: { xs: 'fixed', md: 'sticky' },
        transform: { xs: 'translateX(calc(100% * (var(--SideNavigation-slideIn, 0) - 1)))', md: 'none' },
        transition: 'transform 0.4s, width 0.4s',
        zIndex: 10000,
        height: '100dvh',
        width: '240px',
        top: 0,
        p: 2,
        flexShrink: 0,
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
        borderRight: '1px solid',
        borderColor: 'divider',
      }}
    >
      <GlobalStyles
        styles={(theme) => ({
          ':root': {
            '--Navigation-width': '240px',
          },
        })}
      />
      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
        <IconButton variant="soft" color="primary" size="sm">
          <img src={logo} alt="logo" style={{ width: 60, height: 40 }} />
        </IconButton>
        <Typography level="title-lg">/etc/friends</Typography>
      </Box>

      <Box
        sx={{
          minHeight: 0,
          overflow: 'hidden auto',
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          [`& .${listItemButtonClasses.root}`]: {
            gap: 1.5,
          },
        }}
      >
        <List
          size="sm"
          sx={{
            gap: 1,
            '--List-nestedInsetStart': '30px',
            '--ListItem-radius': (theme) => theme.vars.radius.sm,
          }}
        >
          <ListItem>
            <ListItemButton
              selected={location.pathname === '/inbox'}
              onClick={() => navigate('/inbox')}
            >
              <MaterialIcon><InboxRoundedIcon /></MaterialIcon>
              <ListItemContent>
                <Typography level="title-sm">받은 메일함</Typography>
              </ListItemContent>
              <Chip size="sm" color="primary" variant="solid">
                {inboxCount}
              </Chip>
            </ListItemButton>
          </ListItem>

          <ListItem>
            <ListItemButton
              selected={location.pathname === '/sent' || location.pathname === '/'}
              onClick={() => navigate('/sent')}
              color={location.pathname === '/sent' || location.pathname === '/' ? 'primary' : undefined}
            >
              <MaterialIcon><SendRoundedIcon /></MaterialIcon>
              <ListItemContent>
                <Typography level="title-sm">보낸 메일함</Typography>
              </ListItemContent>
            </ListItemButton>
          </ListItem>
          
        </List>
      </Box>

      <Divider />

      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
        <Avatar variant="outlined" size="sm" src="" />
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography level="title-sm">{getStoredAuthUser()?.username ?? 'admin'}</Typography>
          <Typography level="body-xs">{getStoredAuthUser()?.email ?? 'admin@gmail.com'}</Typography>
        </Box>
        <Tooltip title={isDarkMode ? '라이트 모드' : '다크 모드'}>
          <IconButton
            size="sm"
            variant="plain"
            color="neutral"
            onClick={() => setMode(isDarkMode ? 'light' : 'dark')}
            aria-label={isDarkMode ? '라이트 모드로 변경' : '다크 모드로 변경'}
          >
            <MaterialIcon>
              {isDarkMode ? <LightModeRoundedIcon /> : <DarkModeRoundedIcon />}
            </MaterialIcon>
          </IconButton>
        </Tooltip>
        <Tooltip title={'로그아웃'}>
          <IconButton
            size="sm"
            variant="plain"
            color="neutral"
            onClick={handleLogout}
            aria-label={'로그아웃'}
          >
            <MaterialIcon><LogoutRoundedIcon /></MaterialIcon>
          </IconButton>
        </Tooltip>
      </Box>
    </Sheet>
  );
}
