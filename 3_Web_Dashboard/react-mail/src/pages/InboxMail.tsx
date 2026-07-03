import * as React from 'react';
import Box from '@mui/joy/Box';
import Button from '@mui/joy/Button';
import CssBaseline from '@mui/joy/CssBaseline';
import { CssVarsProvider } from '@mui/joy/styles';
import Typography from '@mui/joy/Typography';
import Sheet from '@mui/joy/Sheet';
import Input from '@mui/joy/Input';
import Divider from '@mui/joy/Divider';
import List from '@mui/joy/List';
import CreateRoundedIcon from '@mui/icons-material/CreateRounded';
import SearchRoundedIcon from '@mui/icons-material/SearchRounded';
import Navigation from '../components/email/Navigation';
import EmailList, { type Email } from '../components/email/EmailList';
import EmailContent from '../components/email/EmailContent';
import ComposeModal from '../components/email/ComposeModal';
import MaterialIcon from '../components/email/MaterialIcon';
import { fetchInboxMails, markMailAsRead } from '../api/mailbox';
import { getStoredAuthUser } from '../api/auth';

const INBOX_EMAILS: Email[] = [];

export default function InboxMail() {
  const [emails, setEmails] = React.useState<Email[]>(INBOX_EMAILS);
  const [selectedEmail, setSelectedEmail] = React.useState<Email | null>(INBOX_EMAILS[0]);
  const [composeOpen, setComposeOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');


  const loadInboxMails = React.useCallback(async () => {
    const user = getStoredAuthUser();
    const email = user?.email ?? 'admin@gmail.com';
    try {
      const data = await fetchInboxMails(email);
      setEmails(data as Email[]);
      setSelectedEmail(data[0] ?? null);
    } catch {
      // API failure: keep current rendered state.
    }
  }, []);

  React.useEffect(() => {
    loadInboxMails();
  }, [loadInboxMails]);

  const handleSelectEmail = (email: Email) => {
    const readEmail = { ...email, unread: false };
    setSelectedEmail(readEmail);

    if (!email.unread) {
      return;
    }

    setEmails((current) =>
      current.map((item) => (item.id === email.id ? { ...item, unread: false } : item)),
    );
    window.dispatchEvent(new CustomEvent('mailbox:inbox-read'));

    markMailAsRead(email.id).catch(() => {
      // 다음 목록 새로고침에서 서버 상태가 다시 반영됩니다.
    });
  };

  const handleDeleted = (mailBoxId: number) => {
    setEmails((current) => {
      const next = current.filter((item) => item.id !== mailBoxId);
      setSelectedEmail(next[0] ?? null);
      return next;
      // Server update failures are reflected on the next list reload.
    });
  };

  const filtered = emails.filter(
    (e) =>
      e.sender.includes(search) ||
      e.subject.includes(search) ||
      e.preview.includes(search),
  );

  return (
    <CssVarsProvider disableTransitionOnChange>
      <CssBaseline />
      <Box sx={{ display: 'flex', minHeight: '100dvh', background: '#f3f6f9' }}>
        <Navigation />

        {/* Email list panel */}
        <Sheet
          sx={{
            width: { xs: '100%', md: 320 },
            flexShrink: 0,
            display: 'flex',
            flexDirection: 'column',
            borderRight: '1px solid',
            borderColor: '#d9e1ea',
            backgroundColor: '#fbfcfe',
          }}
        >
          <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
            <Typography level="title-lg" sx={{ flex: 1, color: '#111827' }}>
              받은 메일함
            </Typography>
            <Button
              variant="solid"
              color="primary"
              size="sm"
              startDecorator={<MaterialIcon><CreateRoundedIcon /></MaterialIcon>}
              onClick={() => setComposeOpen(true)}
              sx={{ borderRadius: 6, fontWeight: 700 }}
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
              sx={{ borderRadius: 6, backgroundColor: '#fff' }}
            />
          </Box>

          <Divider />

          <Box sx={{ flex: 1, overflow: 'auto' }}>
            <List sx={{ p: 0 }}>
              <EmailList
                emails={filtered}
                selectedId={selectedEmail?.id ?? null}
                onSelect={handleSelectEmail}
              />
            </List>
          </Box>
        </Sheet>

        {/* Email content panel */}
        <Box sx={{ flex: 1, overflow: 'hidden' }}>
          <EmailContent email={selectedEmail} onDeleted={handleDeleted} />
        </Box>
      </Box>

      <ComposeModal open={composeOpen} onClose={() => setComposeOpen(false)} />
    </CssVarsProvider>
  );
}
