import * as React from 'react';
import Box from '@mui/joy/Box';
import Button from '@mui/joy/Button';
import CssBaseline from '@mui/joy/CssBaseline';
import { CssVarsProvider } from '@mui/joy/styles';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import Sheet from '@mui/joy/Sheet';
import Input from '@mui/joy/Input';
import Divider from '@mui/joy/Divider';
import IconButton from '@mui/joy/IconButton';
import List from '@mui/joy/List';
import CreateRoundedIcon from '@mui/icons-material/CreateRounded';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import Navigation from '../components/email/Navigation';
import EmailList, { type Email } from '../components/email/EmailList';
import EmailContent from '../components/email/EmailContent';
import ComposeModal from '../components/email/ComposeModal';
import MaterialIcon from '../components/email/MaterialIcon';
import { fetchSentMails } from '../api/mailbox';
import { getStoredAuthUser } from '../api/auth';

const SENT_EMAILS: Email[] = [];

export default function SentMail() {
  const [emails, setEmails] = React.useState<Email[]>(SENT_EMAILS);
  const [selectedEmail, setSelectedEmail] = React.useState<Email | null>(SENT_EMAILS[0]);
  const [composeOpen, setComposeOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');

  const loadSentMails = React.useCallback(async () => {
    const user = getStoredAuthUser();
    const email = user?.email ?? 'admin@gmail.com';
    try {
      const data = await fetchSentMails(email);
      setEmails(data as Email[]);
      setSelectedEmail(data[0] ?? null);
    } catch {
      // API failure: keep current rendered state.
    }
  }, []);

  React.useEffect(() => {
    loadSentMails();
  }, [loadSentMails]);

  const filtered = emails.filter(
    (e) =>
      e.sender.includes(search) ||
      e.subject.includes(search) ||
      e.preview.includes(search),
  );

  return (
    <CssVarsProvider disableTransitionOnChange>
      <CssBaseline />
      <Box sx={{ display: 'flex', minHeight: '100dvh' }}>
        <Navigation />

        {/* Email list panel */}
        <Sheet
          sx={{
            width: 320,
            flexShrink: 0,
            display: 'flex',
            flexDirection: 'column',
            borderRight: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography level="title-lg" sx={{ flex: 1 }}>
              보낸 메일함
            </Typography>
            <Button
              variant="solid"
              color="primary"
              size="sm"
              startDecorator={<MaterialIcon><CreateRoundedIcon /></MaterialIcon>}
              onClick={() => setComposeOpen(true)}
            >
              메일 작성
            </Button>
          </Box>

          <Box sx={{ px: 2, pb: 2 }}>
            <Input
              size="sm"
              startDecorator={<MaterialIcon><SearchRoundedIcon /></MaterialIcon>}
              placeholder="메일 검색..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </Box>

          <Divider />

          <Box sx={{ flex: 1, overflow: 'auto' }}>
            <List sx={{ p: 0 }}>
              <EmailList
                emails={filtered}
                selectedId={selectedEmail?.id ?? null}
                onSelect={setSelectedEmail}
              />
            </List>
          </Box>
        </Sheet>

        {/* Email content panel */}
        <Box sx={{ flex: 1, overflow: 'hidden' }}>
          <EmailContent email={selectedEmail} onDeleted={loadSentMails} />
        </Box>
      </Box>

      <ComposeModal open={composeOpen} onClose={() => setComposeOpen(false)} />
    </CssVarsProvider>
  );
}
