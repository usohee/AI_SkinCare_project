package com.example.mirrorme

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.SmartToy
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.mirrorme.ui.theme.MirrorMeTheme

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReportScreen(
    response: SkinAnalysisResponse,
    onBackClick: () -> Unit = {}
) {
    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        text = "AI 처방전",
                        fontFamily = MM_Font,
                        fontWeight = FontWeight.Bold,
                        fontSize = 18.sp
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = Color.Black
                        )
                    }
                },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(containerColor = Color.White)
            )
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(Color.White)
                .verticalScroll(rememberScrollState())
        ) {
            // 1. 요약 정보 섹션
            SummarySection(response)

            HorizontalDivider(
                modifier = Modifier.padding(horizontal = 20.dp),
                thickness = 1.dp,
                color = Color(0xFFF0F0F0)
            )

            // 2. AI 어드바이스 섹션
            AdviceSection(response.llmReport?.summary)

            Spacer(modifier = Modifier.height(24.dp))
            HorizontalDivider(thickness = 8.dp, color = Color(0xFFF5F5F5))

            // 3. 분석 상세 (점수 기반)
            DetailScoresSection(response.scores)

            Spacer(modifier = Modifier.height(24.dp))
            HorizontalDivider(thickness = 8.dp, color = Color(0xFFF5F5F5))

            // 4. 추천 제품 섹션 (현재 목업 유지 또는 고도화)
            ProductSection()

            Spacer(modifier = Modifier.height(30.dp))
        }
    }
}

@Composable
fun SummarySection(response: SkinAnalysisResponse) {
    Column(modifier = Modifier.padding(horizontal = 20.dp, vertical = 10.dp)) {
        SummaryRow("종합 점수", "${response.totalScore}점")
        
        // 주의 항목 계산 (점수가 높은 것이 안좋은 것 - backend logic: scores = normalize(k, v), total_score = 100 - avg(scores))
        val worstCategory = listOf(
            "여드름" to response.scores.acne,
            "색소침착" to response.scores.pigmentation,
            "모공" to response.scores.pore,
            "피지" to response.scores.sebum
        ).maxByOrNull { it.second }?.first ?: "없음"

        SummaryRow("주의 항목", worstCategory)
        SummaryRow("분석 결과", if (response.totalScore >= 80) "우수" else if (response.totalScore >= 60) "보통" else "주의 필요")
    }
}

@Composable
fun SummaryRow(label: String, value: String) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 12.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(
            text = label,
            fontFamily = MM_Font,
            fontSize = 16.sp,
            fontWeight = FontWeight.Normal,
            color = Color.Black
        )
        Text(
            text = value,
            fontFamily = MM_Font,
            fontSize = 16.sp,
            fontWeight = FontWeight.Normal,
            color = Color.Black
        )
    }
}

@Composable
fun AdviceSection(summary: String?) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp, vertical = 32.dp),
        verticalAlignment = Alignment.Top
    ) {
        // 로봇 아이콘
        Icon(
            imageVector = Icons.Default.SmartToy,
            contentDescription = "AI Robot",
            modifier = Modifier.size(42.dp),
            tint = Color(0xFF9E9E9E)
        )

        Spacer(modifier = Modifier.width(16.dp))

        Box(
            modifier = Modifier
                .weight(1f)
                .background(Color(0xFFF5F5F5), RoundedCornerShape(16.dp))
                .padding(20.dp)
        ) {
            Text(
                text = summary ?: "분석 결과를 바탕으로 AI 리포트를 생성 중입니다...",
                fontFamily = MM_Font,
                fontSize = 15.sp,
                lineHeight = 24.sp,
                color = Color.Black.copy(alpha = 0.8f)
            )
        }
    }
}

@Composable
fun DetailScoresSection(scores: SkinDetails) {
    Column(modifier = Modifier.padding(20.dp)) {
        Text(
            text = "분석 상세 점수 (낮을수록 좋음)",
            fontFamily = MM_Font,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(bottom = 16.dp)
        )
        
        ScoreProgressBar("여드름", scores.acne, Color(0xFF9575CD))
        ScoreProgressBar("색소침착", scores.pigmentation, Color(0xFFFFB74D))
        ScoreProgressBar("모공", scores.pore, Color(0xFF4FC3F7))
        ScoreProgressBar("피지", scores.sebum, Color(0xFFFF8A80))
    }
}

@Composable
fun ScoreProgressBar(label: String, score: Int, color: Color) {
    Column(modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp)) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Text(text = label, fontFamily = MM_Font, fontSize = 14.sp)
            Text(text = "$score/100", fontFamily = MM_Font, fontSize = 14.sp, fontWeight = FontWeight.Bold)
        }
        Spacer(modifier = Modifier.height(4.dp))
        LinearProgressIndicator(
            progress = { score / 100f },
            modifier = Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp)),
            color = color,
            trackColor = Color(0xFFEEEEEE),
        )
    }
}

@Composable
fun ProductSection() {
    Column(modifier = Modifier.padding(20.dp)) {
        Text(
            text = "항목",
            fontFamily = MM_Font,
            fontSize = 20.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(bottom = 24.dp)
        )

        ProductItem(
            brand = "닥터지",
            name = "닥터지 레드블레미쉬 클리어 수딩크림EX 70ml 1+1 기획세트",
        )
        Spacer(modifier = Modifier.height(24.dp))
        ProductItem(
            brand = "셀퓨전씨",
            name = "셀퓨전씨 포스트 알파 쿨링 마스크 1P (퍼스트 쿨링 마스크)",
        )
        Spacer(modifier = Modifier.height(24.dp))
        ProductItem(
            brand = "아토팜",
            name = "아토팜 판테놀 로션 180ml",
        )
    }
}

@Composable
fun ProductItem(brand: String, name: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(80.dp)
                .clip(RoundedCornerShape(12.dp))
                .background(Color(0xFFF5F5F5)),
            contentAlignment = Alignment.Center
        ) {
            Text(
                text = "이미지",
                fontSize = 12.sp,
                color = Color.LightGray,
                fontFamily = MM_Font
            )
        }
        Spacer(modifier = Modifier.width(16.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = brand,
                color = Color.Gray,
                fontSize = 13.sp,
                fontFamily = MM_Font
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = name,
                color = Color.Black,
                fontSize = 15.sp,
                fontFamily = MM_Font,
                fontWeight = FontWeight.Medium,
                lineHeight = 20.sp
            )
        }
    }
}

@Composable
fun ChartSection() {
    val labelPaint = remember {
        android.graphics.Paint().apply {
            color = android.graphics.Color.parseColor("#999999")
            textAlign = android.graphics.Paint.Align.RIGHT
        }
    }

    Column(modifier = Modifier.padding(20.dp)) {
        Text(
            text = "피부 변화 추이",
            fontFamily = MM_Font,
            fontSize = 18.sp,
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(bottom = 24.dp)
        )

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(220.dp)
        ) {
            Canvas(modifier = Modifier.fillMaxSize()) {
                val width = size.width
                val height = size.height
                val paddingLeft = 40.dp.toPx()
                val paddingBottom = 40.dp.toPx()
                val paddingTop = 10.dp.toPx()
                val paddingRight = 10.dp.toPx()

                val chartWidth = width - paddingLeft - paddingRight
                val chartHeight = height - paddingBottom - paddingTop

                // Draw Y-axis grid lines and labels
                val steps = 5
                for (i in 0..steps) {
                    val y = paddingTop + chartHeight - (chartHeight * i / steps)
                    val label = (i * 20).toString()

                    drawLine(
                        color = Color(0xFFF0F0F0),
                        start = Offset(paddingLeft, y),
                        end = Offset(width - paddingRight, y),
                        strokeWidth = 1.dp.toPx()
                    )

                    drawContext.canvas.nativeCanvas.drawText(
                        label,
                        paddingLeft - 10.dp.toPx(),
                        y + 4.dp.toPx(),
                        labelPaint.apply {
                            textSize = 10.sp.toPx()
                        }
                    )
                }

                // Sample Data for trend
                val chartData = listOf(
                    "03.05" to listOf(40, 55, 50, 45),
                    "03.11" to listOf(55, 40, 60, 50),
                    "03.19" to listOf(60, 45, 65, 72)
                )

                val colors = listOf(
                    Color(0xFF9575CD), // acne (여드름) - Purple
                    Color(0xFFFF8A80), // moisture (보습) - Red/Pink
                    Color(0xFF4FC3F7), // pore (모공) - Blue
                    Color(0xFFFFB74D)  // pigmentation (색소) - Orange
                )

                // Draw lines and points for each category
                for (sIndex in 0 until 4) {
                    val points = chartData.mapIndexed { index, data ->
                        val x = paddingLeft + (chartWidth / (chartData.size - 1 + 2)) * (index + 1)
                        val y = paddingTop + chartHeight - (chartHeight * data.second[sIndex] / 100f)
                        Offset(x, y)
                    }

                    // Draw line
                    for (i in 0 until points.size - 1) {
                        drawLine(
                            color = colors[sIndex],
                            start = points[i],
                            end = points[i + 1],
                            strokeWidth = 2.dp.toPx()
                        )
                    }

                    // Draw dots
                    points.forEach { point ->
                        drawCircle(
                            color = Color.White,
                            radius = 4.dp.toPx(),
                            center = point
                        )
                        drawCircle(
                            color = colors[sIndex],
                            radius = 4.dp.toPx(),
                            center = point,
                            style = Stroke(width = 2.dp.toPx())
                        )
                    }
                }

                // Draw X-axis labels (dates)
                chartData.forEachIndexed { index, data ->
                    val x = paddingLeft + (chartWidth / (chartData.size - 1 + 2)) * (index + 1)
                    drawContext.canvas.nativeCanvas.drawText(
                        data.first,
                        x,
                        height - 10.dp.toPx(),
                        labelPaint.apply {
                            textAlign = android.graphics.Paint.Align.CENTER
                            textSize = 11.sp.toPx()
                        }
                    )
                }
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        // Legend
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.Center,
            verticalAlignment = Alignment.CenterVertically
        ) {
            LegendItem(Color(0xFF9575CD), "여드름")
            Spacer(modifier = Modifier.width(16.dp))
            LegendItem(Color(0xFFFF8A80), "보습")
            Spacer(modifier = Modifier.width(16.dp))
            LegendItem(Color(0xFF4FC3F7), "모공")
            Spacer(modifier = Modifier.width(16.dp))
            LegendItem(Color(0xFFFFB74D), "색소")
        }
    }
}

@Composable
fun LegendItem(color: Color, label: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .background(color, CircleShape)
        )
        Spacer(modifier = Modifier.width(4.dp))
        Text(
            text = label,
            fontSize = 12.sp,
            color = Color.Gray,
            fontFamily = MM_Font
        )
    }
}

@Preview(showBackground = true)
@Composable
fun ReportScreenPreview() {
    MirrorMeTheme {
        ReportScreen(
            response = SkinAnalysisResponse(
                success = true,
                totalScore = 78,
                scores = SkinDetails(acne = 75, pigmentation = 60, pore = 70, sebum = 55)
            )
        )
    }
}
