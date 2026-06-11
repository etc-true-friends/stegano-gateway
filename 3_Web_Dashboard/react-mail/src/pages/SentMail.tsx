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

const SENT_EMAILS: Email[] = [
  {
    id: 1,
    sender: '홍길동',
    subject: '프로젝트 진행 현황 보고',
    preview: '안녕하세요, 이번 주 프로젝트 진행 현황을 보고 드립니다. 현재 백엔드 API 연동 작업이 70% 완료되었으며...',
    date: '오늘 10:30',
    unread: false,
    avatarColor: 'primary.softBg',
  },
  {
    id: 2,
    sender: '김철수',
    subject: '[공지] 주간 미팅 일정 안내',
    preview: '안녕하세요. 이번 주 금요일 오후 3시에 주간 미팅이 예정되어 있습니다. 준비 자료를 미리 공유해 주시기 바랍니다.',
    date: '어제 15:22',
    unread: false,
    avatarColor: 'success.softBg',
  },
  {
    id: 3,
    sender: '이영희',
    subject: '이미지 스테가노그래피 분석 결과',
    preview: '첨부 파일에 분석 결과를 정리해 두었습니다. 총 5개의 이미지에서 숨겨진 데이터가 발견되었으며...',
    date: '2일 전',
    unread: false,
    avatarColor: 'warning.softBg',
  },
  {
    id: 4,
    sender: 'security@example.com',
    subject: '보안 감사 보고서 제출',
    preview: '지난 분기 보안 감사 결과를 첨부 파일로 제출합니다. 검토 후 피드백 부탁드립니다.',
    date: '3일 전',
    unread: false,
    avatarColor: 'danger.softBg',
  },
  {
    id: 5,
    sender: '박민준',
    subject: 'API 명세서 검토 요청',
    preview: '안녕하세요. 스테가노그래피 게이트웨이 API 명세서 초안을 작성하였습니다. 검토 부탁드립니다.',
    date: '4일 전',
    unread: false,
  },
];

export default function SentMail() {
  const [selectedEmail, setSelectedEmail] = React.useState<Email | null>(SENT_EMAILS[0]);
  const [composeOpen, setComposeOpen] = React.useState(false);
  const [search, setSearch] = React.useState('');

  const filtered = SENT_EMAILS.filter(
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

        {/* 이메일 목록 패널 */}
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
              startDecorator={<CreateRoundedIcon />}
              onClick={() => setComposeOpen(true)}
            >
              메일 작성
            </Button>
          </Box>

          <Box sx={{ px: 2, pb: 2 }}>
            <Input
              size="sm"
              startDecorator={<SearchRoundedIcon />}
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

        {/* 이메일 내용 패널 */}
        <Box sx={{ flex: 1, overflow: 'hidden' }}>
          <EmailContent email={selectedEmail} />
        </Box>
      </Box>

      <ComposeModal open={composeOpen} onClose={() => setComposeOpen(false)} />
    </CssVarsProvider>
  );
}
