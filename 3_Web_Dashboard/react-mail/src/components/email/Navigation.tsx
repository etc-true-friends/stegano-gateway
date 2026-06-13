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
import InboxRoundedIcon from '@mui/icons-material/InboxRounded';
import SendRoundedIcon from '@mui/icons-material/SendRounded';
import DeleteRoundedIcon from '@mui/icons-material/DeleteRounded';
import LogoutRoundedIcon from '@mui/icons-material/LogoutRounded';
import { useNavigate, useLocation } from 'react-router-dom';

export default function Navigation() {
  const navigate = useNavigate();
  const location = useLocation();

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
          <img src="/logo.png" alt="logo" style={{ width: 20, height: 20 }} />
        </IconButton>
        <Typography level="title-lg">ETC Friends</Typography>
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
              <InboxRoundedIcon />
              <ListItemContent>
                <Typography level="title-sm">받은 메일함</Typography>
              </ListItemContent>
              <Chip size="sm" color="primary" variant="solid">
                12
              </Chip>
            </ListItemButton>
          </ListItem>

          <ListItem>
            <ListItemButton
              selected={location.pathname === '/sent' || location.pathname === '/'}
              onClick={() => navigate('/sent')}
              color={location.pathname === '/sent' || location.pathname === '/' ? 'primary' : undefined}
            >
              <SendRoundedIcon />
              <ListItemContent>
                <Typography level="title-sm">보낸 메일함</Typography>
              </ListItemContent>
            </ListItemButton>
          </ListItem>

          <ListItem>
            <ListItemButton
              selected={location.pathname === '/trash'}
              onClick={() => navigate('/trash')}
            >
              <DeleteRoundedIcon />
              <ListItemContent>
                <Typography level="title-sm">휴지통</Typography>
              </ListItemContent>
            </ListItemButton>
          </ListItem>
        </List>
      </Box>

      <Divider />

      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
        <Avatar variant="outlined" size="sm" src="" />
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography level="title-sm">관리자</Typography>
          <Typography level="body-xs">admin@etcfriends.com</Typography>
        </Box>
        <IconButton size="sm" variant="plain" color="neutral">
          <LogoutRoundedIcon />
        </IconButton>
      </Box>
    </Sheet>
  );
}
