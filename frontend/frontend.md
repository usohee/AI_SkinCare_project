frontend/app/src/main/
├── AndroidManifest.xml (인터넷 권한 설정)
└── java/com/example/mirrorme/
    ├── MainActivity.kt (앱 실행 진입점)
    ├── AnalysisScreen.kt (Jetpack Compose 피부 진단 UI 화면)
    ├── RetrofitClient.kt (FastAPI 서버 연결 설정 객체)
    ├── SkinApiService.kt (HTTP Multipart 이미지 전송 인터페이스)
    └── SkinAnalysisResponse.kt (피부 결과 및 LLM 리포트 파싱용 데이터 클래스)
