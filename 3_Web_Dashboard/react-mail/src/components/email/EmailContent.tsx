import * as React from 'react';
import Avatar from '@mui/joy/Avatar';
import Box from '@mui/joy/Box';
import Button from '@mui/joy/Button';
import Chip from '@mui/joy/Chip';
import CircularProgress from '@mui/joy/CircularProgress';
import Divider from '@mui/joy/Divider';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import Sheet from '@mui/joy/Sheet';
import DeleteRoundedIcon from '@mui/icons-material/DeleteRounded';
import ForwardToInboxRoundedIcon from '@mui/icons-material/ForwardToInboxRounded';
import ReplyRoundedIcon from '@mui/icons-material/ReplyRounded';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded';
import type { Email } from './EmailList';
import MaterialIcon from './MaterialIcon';
import { formatMailDate } from '../../utils/formatMailDate';
import { fetchMailDetail, fetchAttachmentDownloadUrl, type Attachment } from '../../api/mailbox';
import { deleteMail } from '../../api/mail';

type Props = {
  email: Email | null;
  onDeleted?: (mailBoxId: number) => void;
};

export default function EmailContent({ email, onDeleted }: Props) {
  const [attachments, setAttachments] = React.useState<Attachment[]>([]);
  const [body, setBody] = React.useState<string>('');
  const [downloading, setDownloading] = React.useState<number | null>(null);

  React.useEffect(() => {
    if (!email) return;
    setAttachments([]);
    setBody('');
    fetchMailDetail(email.id).then((detail) => {
      setAttachments(detail.attachments);
      setBody(detail.body);
    }).catch(() => {});
  }, [email?.id]);

  const handleDelete = async () => {
    if (!email) return;
    const { id } = await deleteMail(email.id);
    onDeleted?.(id);
  };

  const handleDownload = async (attachment: Attachment) => {
    setDownloading(attachment.attachmentId);
    try {
      const url = await fetchAttachmentDownloadUrl(attachment.attachmentId);
      window.open(url, '_blank');
    } catch {
      alert('다운로드에 실패했습니다.');
    } finally {
      setDownloading(null);
    }
  };

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
        <Button
          variant="plain"
          color="danger"
          size="sm"
          startDecorator={<MaterialIcon><DeleteRoundedIcon /></MaterialIcon>}
          onClick={handleDelete}
        >
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
            <Typography level="title-sm">
              {email.sender}{' '}
              <Typography component="span" level="body-sm" sx={{ color: 'text.secondary' }}>
                {email.email ? `<${email.email}>` : ''}
              </Typography>
            </Typography>
            <Typography level="body-xs" color="neutral">
              {formatMailDate(email.date)}
            </Typography>
          </Box>
        </Stack>

        <Divider sx={{ mb: 3 }} />

        <Typography level="body-md" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.8, mb: 3 }}>
          {body || email.preview}
        </Typography>

        {attachments.length > 0 && (
          <>
            <Divider sx={{ mb: 2 }} />
            <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1.5 }}>
              <MaterialIcon><AttachFileIcon sx={{ fontSize: 16, color: 'text.secondary' }} /></MaterialIcon>
              <Typography level="body-sm" color="neutral">
                첨부파일 {attachments.length}개
              </Typography>
            </Stack>
            <Stack spacing={1}>
              {attachments.map((att) => (
                <Chip
                  key={att.attachmentId}
                  variant="outlined"
                  color="neutral"
                  size="md"
                  startDecorator={<MaterialIcon><AttachFileIcon sx={{ fontSize: 14 }} /></MaterialIcon>}
                  endDecorator={
                    downloading === att.attachmentId
                      ? <CircularProgress size="sm" sx={{ '--CircularProgress-size': '16px' }} />
                      : <MaterialIcon><DownloadRoundedIcon sx={{ fontSize: 14 }} /></MaterialIcon>
                  }
                  onClick={() => handleDownload(att)}
                  sx={{ cursor: 'pointer', alignSelf: 'flex-start' }}
                >
                  {att.fileName}
                </Chip>
              ))}
            </Stack>
          </>
        )}
      </Box>
    </Sheet>
  );
}