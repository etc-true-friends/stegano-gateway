import * as React from 'react';
import Avatar from '@mui/joy/Avatar';
import Box from '@mui/joy/Box';
import Button from '@mui/joy/Button';
import Chip from '@mui/joy/Chip';
import CircularProgress from '@mui/joy/CircularProgress';
import Divider from '@mui/joy/Divider';
import Modal from '@mui/joy/Modal';
import ModalDialog from '@mui/joy/ModalDialog';
import DialogTitle from '@mui/joy/DialogTitle';
import DialogContent from '@mui/joy/DialogContent';
import DialogActions from '@mui/joy/DialogActions';
import Stack from '@mui/joy/Stack';
import Typography from '@mui/joy/Typography';
import Sheet from '@mui/joy/Sheet';
import DeleteRoundedIcon from '@mui/icons-material/DeleteRounded';
import ForwardToInboxRoundedIcon from '@mui/icons-material/ForwardToInboxRounded';
import ReplyRoundedIcon from '@mui/icons-material/ReplyRounded';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import DownloadRoundedIcon from '@mui/icons-material/DownloadRounded';
import WarningRoundedIcon from '@mui/icons-material/WarningRounded';
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
  const [deleteOpen, setDeleteOpen] = React.useState(false);
  const [deleting, setDeleting] = React.useState(false);

  React.useEffect(() => {
    if (!email) return;
    setAttachments([]);
    setBody('');
    fetchMailDetail(email.id).then((detail) => {
      setAttachments(detail.attachments);
      setBody(detail.body);
    }).catch(() => {});
  }, [email?.id]);

  const handleConfirmDelete = async () => {
    if (!email) return;
    setDeleting(true);
    try {
      const { id } = await deleteMail(email.id);
      setDeleteOpen(false);
      onDeleted?.(id);
    } finally {
      setDeleting(false);
    }
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
          background: '#f3f6f9',
        }}
      >
        <Typography level="body-md" color="neutral">
          메일을 선택해주세요.
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
        background: '#f3f6f9',
      }}
    >
      <Box sx={{ px: 3, py: 1.5, display: 'flex', alignItems: 'center', gap: 1, backgroundColor: '#f7f9fb' }}>
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
          onClick={() => setDeleteOpen(true)}
        >
          삭제
        </Button>
      </Box>

      <Divider />

      <Box sx={{ p: { xs: 2, md: 3 }, flex: 1 }}>
        <Sheet
          variant="plain"
          sx={{
            minHeight: 'calc(100dvh - 116px)',
            p: { xs: 2, md: 3 },
            backgroundColor: '#f3f6f9',
          }}
        >
          <Typography level="h3" sx={{ mb: 2, color: '#111827', letterSpacing: 0 }}>
            {email.subject}
          </Typography>

          <Stack direction="row" spacing={2} alignItems="flex-start" sx={{ mb: 3 }}>
            <Avatar sx={{ mt: 0.5, backgroundColor: '#e4eefb', color: '#1f4f8f' }}>
              {email.sender[0].toUpperCase()}
            </Avatar>
            <Box sx={{ minWidth: 0 }}>
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

          <Typography level="body-md" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.8, mb: 3, color: '#1f2937' }}>
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
                    sx={{ cursor: 'pointer', alignSelf: 'flex-start', borderRadius: 6, backgroundColor: '#fff' }}
                  >
                    {att.fileName}
                  </Chip>
                ))}
              </Stack>
            </>
          )}
        </Sheet>
      </Box>

      <Modal open={deleteOpen} onClose={() => !deleting && setDeleteOpen(false)}>
        <ModalDialog
          variant="outlined"
          role="alertdialog"
          sx={{ width: 380, borderRadius: 6 }}
        >
          <DialogTitle>
            <MaterialIcon><WarningRoundedIcon color="warning" /></MaterialIcon>
            메일 삭제
          </DialogTitle>
          <DialogContent>
            정말 이 메일을 삭제하시겠습니까? 삭제한 메일은 목록에서 제거됩니다.
          </DialogContent>
          <DialogActions>
            <Button
              variant="solid"
              color="danger"
              loading={deleting}
              onClick={handleConfirmDelete}
            >
              삭제
            </Button>
            <Button
              variant="plain"
              color="neutral"
              disabled={deleting}
              onClick={() => setDeleteOpen(false)}
            >
              취소
            </Button>
          </DialogActions>
        </ModalDialog>
      </Modal>
    </Sheet>
  );
}
