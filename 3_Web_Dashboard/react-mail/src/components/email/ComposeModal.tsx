import * as React from 'react';
import Box from '@mui/joy/Box';
import Button from '@mui/joy/Button';
import Chip from '@mui/joy/Chip';
import Divider from '@mui/joy/Divider';
import FormControl from '@mui/joy/FormControl';
import FormHelperText from '@mui/joy/FormHelperText';
import FormLabel from '@mui/joy/FormLabel';
import IconButton from '@mui/joy/IconButton';
import Input from '@mui/joy/Input';
import Modal from '@mui/joy/Modal';
import ModalClose from '@mui/joy/ModalClose';
import ModalDialog from '@mui/joy/ModalDialog';
import Stack from '@mui/joy/Stack';
import Textarea from '@mui/joy/Textarea';
import Typography from '@mui/joy/Typography';
import SendRoundedIcon from '@mui/icons-material/SendRounded';
import AttachFileRoundedIcon from '@mui/icons-material/AttachFileRounded';
import CloseRoundedIcon from '@mui/icons-material/CloseRounded';
import InsertDriveFileRoundedIcon from '@mui/icons-material/InsertDriveFileRounded';

type Props = {
  open: boolean;
  onClose: () => void;
};

const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ComposeModal({ open, onClose }: Props) {
  const [to, setTo] = React.useState('');
  const [toTouched, setToTouched] = React.useState(false);
  const [subject, setSubject] = React.useState('');
  const [body, setBody] = React.useState('');
  const [attachments, setAttachments] = React.useState<File[]>([]);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const toError = toTouched && to.length > 0 && !EMAIL_REGEX.test(to);
  const isValid = EMAIL_REGEX.test(to) && !!subject;

  const handleAttachClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? []);
    setAttachments((prev) => [...prev, ...files]);
    // input 초기화해서 같은 파일 재선택 가능하게
    e.target.value = '';
  };

  const handleRemoveAttachment = (idx: number) => {
    setAttachments((prev) => prev.filter((_, i) => i !== idx));
  };

  const handleSend = () => {
    if (!isValid) return;
    console.log('메일 전송:', { to, subject, body, attachments });
    onClose();
    setTo('');
    setToTouched(false);
    setSubject('');
    setBody('');
    setAttachments([]);
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      slotProps={{ backdrop: { sx: { backdropFilter: 'none', backgroundColor: 'transparent' } } }}
    >
      <ModalDialog
        size="lg"
        sx={{
          width: { xs: '95vw', sm: 600 },
          maxHeight: '90vh',
          p: 0,
          overflow: 'hidden',
        }}
      >
        <Box
          sx={{
            px: 3,
            py: 2,
            display: 'flex',
            alignItems: 'center',
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Typography level="title-md" sx={{ flex: 1 }}>
            새 메일 작성
          </Typography>
          <ModalClose sx={{ position: 'static' }} />
        </Box>

        <Stack sx={{ px: 3, py: 2, gap: 1.5, overflow: 'auto', flex: 1 }}>
          <FormControl error={toError}>
            <FormLabel>받는 사람</FormLabel>
            <Input
              placeholder="이메일 주소 입력"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              onBlur={() => setToTouched(true)}
            />
            {toError && (
              <FormHelperText>올바른 이메일 형식이 아닙니다.</FormHelperText>
            )}
          </FormControl>

          <FormControl>
            <FormLabel>제목</FormLabel>
            <Input
              placeholder="제목 입력"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
            />
          </FormControl>

          <Divider />

          <FormControl sx={{ flex: 1 }}>
            <Textarea
              placeholder="메일 내용을 입력하세요..."
              minRows={8}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              sx={{ flex: 1 }}
            />
          </FormControl>

          {attachments.length > 0 && (
            <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
              {attachments.map((file, idx) => (
                <Chip
                  key={idx}
                  size="md"
                  variant="soft"
                  color="neutral"
                  startDecorator={<InsertDriveFileRoundedIcon />}
                  endDecorator={
                    <IconButton
                      size="md"
                      variant="plain"
                      color="neutral"
                      onClick={() => handleRemoveAttachment(idx)}
                      sx={{ '--IconButton-size': '28px', pointerEvents: 'all' }}
                    >
                      <CloseRoundedIcon />
                    </IconButton>
                  }
                  sx={{ fontSize: 'sm', py: 0.5 }}
                >
                  {file.name}
                </Chip>
              ))}
            </Box>
          )}
        </Stack>

        <Box
          sx={{
            px: 3,
            py: 2,
            display: 'flex',
            gap: 1,
            alignItems: 'center',
            borderTop: '1px solid',
            borderColor: 'divider',
          }}
        >
          <input
            ref={fileInputRef}
            type="file"
            multiple
            style={{ display: 'none' }}
            onChange={handleFileChange}
          />
          <IconButton
            variant="outlined"
            color="neutral"
            aria-label="첨부파일"
            onClick={handleAttachClick}
          >
            <AttachFileRoundedIcon />
          </IconButton>
          <Box sx={{ flex: 1 }} />
          <Button
            variant="solid"
            color="primary"
            endDecorator={<SendRoundedIcon />}
            onClick={handleSend}
            disabled={!isValid}
          >
            전송
          </Button>
        </Box>
      </ModalDialog>
    </Modal>
  );
}
