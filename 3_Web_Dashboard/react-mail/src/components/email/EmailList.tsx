import * as React from 'react';
import Avatar from '@mui/joy/Avatar';
import Box from '@mui/joy/Box';
import ListDivider from '@mui/joy/ListDivider';
import ListItem from '@mui/joy/ListItem';
import ListItemButton from '@mui/joy/ListItemButton';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import CircleIcon from '@mui/icons-material/Circle';
import MaterialIcon from './MaterialIcon';
import { formatMailDate } from '../../utils/formatMailDate';

export type Email = {
  id: number;
  email?: string;
  sender: string;
  subject: string;
  preview: string;
  date: string;
  unread: boolean;
  avatarColor?: string;
};

type Props = {
  emails: Email[];
  selectedId: number | null;
  onSelect: (email: Email) => void;
};

export default function EmailList({ emails, selectedId, onSelect }: Props) {
  return (
    <Box sx={{ width: '100%' }}>
      {emails.map((email, idx) => (
        <React.Fragment key={email.id}>
          <ListItem sx={{ p: 0 }}>
            <ListItemButton
              onClick={() => onSelect(email)}
              selected={selectedId === email.id}
              sx={{
                flexDirection: 'column',
                alignItems: 'initial',
                gap: 1,
                p: 2,
                minHeight: 102,
                borderRadius: 0,
                backgroundColor: selectedId === email.id ? '#dcecff' : '#fbfcfe',
                '&:hover': {
                  backgroundColor: selectedId === email.id ? '#dcecff' : '#f0f5fa',
                },
                '&.Mui-selected': {
                  backgroundColor: '#dcecff',
                  boxShadow: 'inset 3px 0 0 #2f6fd6',
                },
              }}
            >
              <Stack direction="row" spacing={1.5}>
                <Avatar
                  sx={{
                    bgcolor: email.avatarColor ?? '#e8f1ff',
                    color: '#1f4f8f',
                    flexShrink: 0,
                  }}
                  size="sm"
                >
                  {email.sender[0].toUpperCase()}
                </Avatar>
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                    <Typography
                      level="title-sm"
                      noWrap
                      sx={{ color: '#111827', fontWeight: email.unread ? 800 : 600 }}
                    >
                      {email.sender}
                    </Typography>
                    <Typography level="body-xs" sx={{ flexShrink: 0, ml: 1, color: '#56657a' }}>
                      {formatMailDate(email.date)}
                    </Typography>
                  </Box>
                  <Typography level="body-sm" noWrap sx={{ color: '#172033', fontWeight: email.unread ? 700 : 500 }}>
                    {email.subject}
                  </Typography>
                </Box>
                {email.unread && (
                  <MaterialIcon>
                    <CircleIcon sx={{ fontSize: 9, color: '#2f6fd6', mt: 0.5 }} />
                  </MaterialIcon>
                )}
              </Stack>
              <Typography
                level="body-sm"
                sx={{
                  display: '-webkit-box',
                  WebkitLineClamp: 2,
                  WebkitBoxOrient: 'vertical',
                  overflow: 'hidden',
                  color: '#344256',
                  lineHeight: 1.55,
                }}
              >
                {email.preview}
              </Typography>
            </ListItemButton>
          </ListItem>
          {idx < emails.length - 1 && <ListDivider sx={{ m: 0 }} />}
        </React.Fragment>
      ))}
    </Box>
  );
}
