import * as React from 'react';
import Avatar from '@mui/joy/Avatar';
import Box from '@mui/joy/Box';
import Button from '@mui/joy/Button';
import Divider from '@mui/joy/Divider';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import Sheet from '@mui/joy/Sheet';
import DeleteRoundedIcon from '@mui/icons-material/DeleteRounded';
import ForwardToInboxRoundedIcon from '@mui/icons-material/ForwardToInboxRounded';
import ReplyAllRoundedIcon from '@mui/icons-material/ReplyAllRounded';
import ReplyRoundedIcon from '@mui/icons-material/ReplyRounded';
import type { Email } from './EmailList';
import MaterialIcon from './MaterialIcon';
import { formatMailDate } from '../../utils/formatMailDate';

type Props = {
  email: Email | null;
};

export default function EmailContent({ email }: Props) {
  if (!email) {
    return (
      <Sheet
        variant="soft"
        sx={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100dvh',
        }}
      >
        <Typography level="body-md" color="neutral">
          메일을 선택하세요
        </Typography>
      </Sheet>
    );
  }

  return (
    <Sheet
      variant="soft"
      sx={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        height: '100dvh',
        overflow: 'auto',
      }}
    >
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <Button variant="plain" color="neutral" size="sm" startDecorator={<MaterialIcon><ReplyRoundedIcon /></MaterialIcon>}>
          답장
        </Button>
        <Button variant="plain" color="neutral" size="sm" startDecorator={<MaterialIcon><ForwardToInboxRoundedIcon /></MaterialIcon>}>
          전달
        </Button>
        <Box sx={{ flex: 1 }} />
        <Button variant="plain" color="danger" size="sm" startDecorator={<MaterialIcon><DeleteRoundedIcon /></MaterialIcon>}>
          삭제
        </Button>
      </Box>

      <Divider />

      <Box sx={{ p: 3, flex: 1 }}>
        <Typography level="h3" sx={{ mb: 2 }}>
          {email.subject}
        </Typography>

        <Stack direction="row" spacing={2} alignItems="flex-start" sx={{ mb: 3 }}>
          <Avatar sx={{ mt: 0.5 }}>{email.sender[0].toUpperCase()}</Avatar>
          <Box>
            <Typography level="title-sm">{email.sender}</Typography>
            <Typography level="body-xs" color="neutral">
              {formatMailDate(email.date)}
            </Typography>
          </Box>
        </Stack>

        <Divider sx={{ mb: 3 }} />

        <Typography level="body-md" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.8 }}>
          {email.preview}
          {'\n\n'}안녕하세요,{'\n\n'}
          이 메일은 보낸 메일함 예시입니다.{'\n\n'}
          감사합니다.
        </Typography>
      </Box>

    </Sheet>
  );
}
