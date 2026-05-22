# 🧴 AI 스킨케어 서비스 "Mirror Me" 
> **OpenCV와 YOLOv8 기반의 고정밀 피부 분석 및 맞춤형 케어 솔루션**

---

## 👋 프로젝트 소개
**Mirror Me**는 고가의 전문 진단 기기 없이 스마트폰 사진 한 장으로 정밀한 피부 상태를 파악하는 AI 기반 헬스케어 서비스입니다.  
단순한 진단을 넘어, 사용자가 보유한 화장품과의 적합성을 판별하고 최적의 스킨케어 루틴을 제안하여 정보의 비대칭성과 경제적 부담을 해결합니다. 



### 🎯 프로젝트 핵심 목표
- **접근성 제고**: 스마트폰/웹캠을 통한 정밀 진단 환경 구축 
- **객관적 지표 제공**: 여드름, 모공, 홍조, 피지 반사 등 4가지 지표 수치화 
- **지능형 큐레이션**: LLM 기반의 제품 적합성 판단 및 루틴 생성
- **신뢰성 확보**: 식약처 고시 성분 및 대한피부과의사회 가이드라인 준수

---

## 📌 주요 기능 소개

### 1️⃣ Computer Vision 기반 고정밀 진단
- **피부 영역(ROI) 자동 추출**: 사용자가 업로드한 이미지에서 분석 영역 설정
- **4대 지표 분석**: 여드름 개수, 모공 크기, 홍조 영역, 피지 반사 탐지
- **정량적 점수화**: 분석 데이터를 100점 만점 기준으로 환산하여 DB 기록

### 2️⃣ 생성형 AI 기반 맞춤 처방전
- **피부 고민 심층 분석**: 점수화된 데이터를 자연어로 해석하여 근본 원인 도출
- **소장 제품 적합성 판별**: 크롤링된 전성분 데이터와 사용자 피부 타입 비교
- **스마트 루틴 설계**: 아침/저녁 맞춤형 스킨케어 루틴 자동 생성

### 3️⃣ 시각화 리포트 제공
- **변화 추적**: 과거 대비 점수 변화를 꺾은선 그래프로 시각화
- **성분 보강 추천**: 현재 루틴에서 부족한 성분을 보강할 제품 추천

---

## 🛠 Tech Stack
- **AI/Analysis**: Python, OpenCV, YOLOv8, Roboflow 
- **LLM**: ChatGPT, Claude, GitHub Copilot 
- **Database**: 공공데이터포털 API, 전성분 크롤링 DB 
- **Design**: Figma, Android Studio 

---

## 🤝 팀원 소개

<table>
  <tr>
    <td align="center" width="100px"><b>프로필</b></td>
    <td align="center" width="100px"><b>성명</b></td>
    <td align="center" width="50px"><b>학번</b></td>
    <td align="center" width="350px"><b>역할 및 링크</b></td>
  </tr>
  <tr>
    <td align="center"><img src="https://github.com/usohee.png" width="100px" style="border-radius: 50%;" /></td>
    <td align="center"><b>유소희</b></td>
    <td align="center">20232346</td>
    <td>
      • <b>Role:</b> 알고리즘 설계 & 프로젝트 총괄 <br>
      • <b>GitHub:</b> <a href="https://github.com/usohee/2026_Capstone">@usohee</a>
    </td>
  </tr>
  <tr>
    <td align="center"><img src="https://github.com/yejin135.png" width="100px" style="border-radius: 50%;" /></td>
    <td align="center"><b>현예진</b></td>
    <td align="center">20241512</td>
    <td>
      • <b>Role:</b> 백엔드 & DB 설계 <br>
      • <b>GitHub:</b> <a href="https://github.com/yejin135/2026-Capstone">@yejin135</a>
    </td>
  </tr>
  <tr>
    <td align="center"><img src="https://github.com/yeojeong735.png" width="100px" style="border-radius: 50%;" /></td>
    <td align="center"><b>장여정</b></td>
    <td align="center">20241513</td>
    <td>
      • <b>Role:</b> 프론트엔드 개발 <br>
      • <b>GitHub:</b> <a href="https://github.com/yeojeong735/2026-Capstone">@yeojeong735</a>
    </td>
  </tr>
  <tr>
    <td align="center"><img src="https://github.com/leeyunseok110.png" width="100px" style="border-radius: 50%;" /></td>
    <td align="center"><b>이윤석</b></td>
    <td align="center">20242523</td>
    <td>
      • <b>Role:</b> AI 프롬프트 엔지니어링 <br>
      • <b>GitHub:</b> <a href="https://github.com/leeyunseok110/2026-Capstone">@leeyunseok110</a>
    </td>
  </tr>
  <tr>
    <td align="center"><img src="https://github.com/jojeongin313.png" width="100px" style="border-radius: 50%;" /></td>
    <td align="center"><b>조정인</b></td>
    <td align="center">20242522</td>
    <td>
      • <b>Role:</b> 데이터 분석 및 처리 <br>
      • <b>GitHub:</b> <a href="https://github.com/jojeongin313/2026-Capstone">@jojeongin313</a>
    </td>
  </tr>
  <tr>
    <td align="center"><img src="https://github.com/pcw11.png" width="100px" style="border-radius: 50%;" /></td>
    <td align="center"><b>박채원</b></td>
    <td align="center">20241487</td>
    <td>
      • <b>Role:</b> 시스템 통합 및 QA <br>
      • <b>GitHub:</b> <a href="https://github.com/pcw11/2026-capstone">@pcw11</a>
    </td>
  </tr>
</table>

<a href="https://www.notion.so/Capstone_project-31fac7b4a84b80bdb95bed53b1432ed3">
<img src="https://img.shields.io/badge/Notion%20Portfolio-332b24?style=for-the-badge&logo=notion&logoColor=ffe5ed"> 
</a>

