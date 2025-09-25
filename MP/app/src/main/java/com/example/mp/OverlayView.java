package com.example.mp;

import android.content.Context;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.PointF;
import android.util.AttributeSet;
import android.view.View;
import com.chaquo.python.PyObject;
import java.util.List;

public class OverlayView extends View {

    private final Paint paint;
    private PointF[] corners;
    private int imageWidth;
    private int imageHeight;

    public OverlayView(Context context, AttributeSet attrs) {
        super(context, attrs);
        paint = new Paint();
        paint.setColor(Color.GREEN);
        paint.setStyle(Paint.Style.STROKE);
        paint.setStrokeWidth(8f);
    }

    public void setCorners(PyObject pyCorners, int width, int height) {
        if (pyCorners == null) {
            this.corners = null;
        } else {
            List<PyObject> cornerList = pyCorners.asList();
            this.corners = new PointF[cornerList.size()];
            for (int i = 0; i < cornerList.size(); i++) {
                List<PyObject> point = cornerList.get(i).asList();
                this.corners[i] = new PointF(point.get(0).toFloat(), point.get(1).toFloat());
            }
        }
        this.imageWidth = width;
        this.imageHeight = height;
        postInvalidate(); // Trigger a redraw
    }

    public void clear() {
        this.corners = null;
        postInvalidate();
    }

    @Override
    protected void onDraw(Canvas canvas) {
        super.onDraw(canvas);
        if (corners != null && imageWidth > 0 && imageHeight > 0) {
            float scaleX = (float) getWidth() / imageWidth;
            float scaleY = (float) getHeight() / imageHeight;
            for (int i = 0; i < corners.length; i++) {
                PointF p1 = corners[i];
                PointF p2 = corners[(i + 1) % corners.length];
                float startX = p1.x * scaleX;
                float startY = p1.y * scaleY;
                float endX = p2.x * scaleX;
                float endY = p2.y * scaleY;
                canvas.drawLine(startX, startY, endX, endY, paint);
            }
        }
    }
}