# 코드R (세가 새턴 일본판) 한글 패치

- 원본: `Code R (Japan)` (4트랙, 트랙 1 에만 패치, 트랙 2~4·cue 그대로)
- 배포 파일은 릴리즈의 zip(xdelta + 적용 bat + readme)을 쓰세요.
- 도구: `tools/tr_fix.py`(받은 번역 검수·자동 수정·창 폭 다시 접기) → `tools/build.py`(대사·글꼴·그림·이름 입력·음성 자막·디스크) → `tools/make_dist.py`(배포 묶음)
- 번역 표: `work/tr/coder_*.tsv`(검수본), 손 수정 `work/tr_manual.tsv`, 음성 자막 `work/voice/*.tsv`
- 조사·결정 기록: `docs/00_초기조사.md`
