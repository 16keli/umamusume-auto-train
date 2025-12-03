import cv2
import numpy as np


def match_template(template, screen, threshold=0.85):
    # Get screenshot
    screen = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)

    #  cv2.namedWindow("image")
    #  cv2.moveWindow("image", -900, 0)
    #  cv2.imshow("image", screen)
    #  cv2.waitKey(5)

    # Load template
    template = cv2.cvtColor(template, cv2.COLOR_RGB2GRAY)
    result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
    loc = np.where(result >= threshold)

    h, w = template.shape[:2]
    boxes = [(x, y, w, h) for (x, y) in zip(*loc[::-1])]

    return deduplicate_boxes(boxes)


def multi_match_templates(templates, screen, threshold=0.85):
    screen_bgr = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)

    cv2.imwrite("debug/screen.png", screen_bgr)

    results = {}
    for name, template in templates.items():
        if template is None:
            results[name] = []
            continue
        template = cv2.cvtColor(template, cv2.COLOR_RGB2GRAY)

        cv2.imwrite(f"debug/template_{name}.png", template)

        result = cv2.matchTemplate(screen_bgr, template, cv2.TM_CCOEFF_NORMED)
        loc = np.where(result >= threshold)
        h, w = template.shape[:2]
        boxes = [(x, y, w, h) for (x, y) in zip(*loc[::-1])]
        results[name] = boxes
    return results


def deduplicate_boxes(boxes, min_dist=5):
    filtered = []
    for x, y, w, h in boxes:
        cx, cy = x + w // 2, y + h // 2
        if all(
            abs(cx - (fx + fw // 2)) > min_dist or abs(cy - (fy + fh // 2)) > min_dist for fx, fy, fw, fh in filtered
        ):
            filtered.append((x, y, w, h))
    return filtered


def is_btn_active(screen, threshold=150):
    grayscale = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
    stat = cv2.mean(grayscale)
    avg_brightness = stat[0]

    # Treshold btn
    return avg_brightness > threshold


def count_pixels_of_color(color_rgb=[117, 117, 117], screen=None, tolerance=2):
    # [117,117,117] is gray for missing energy, we go 2 below and 2 above so that it's more stable in recognition
    if screen is None:
        return -1

    color = np.array(color_rgb, np.uint8)

    # define min/max range ±2
    color_min = np.clip(color - tolerance, 0, 255)
    color_max = np.clip(color + tolerance, 0, 255)

    dst = cv2.inRange(screen, color_min, color_max)
    pixel_count = cv2.countNonZero(dst)
    return pixel_count


def closest_color(color_dict, target_color):
    closest_name = None
    min_dist = float("inf")
    target_color = np.array(target_color)
    for name, col in color_dict.items():
        col = np.array(col)
        dist = np.linalg.norm(target_color - col)  # Euclidean distance
        if dist < min_dist:
            min_dist = dist
            closest_name = name
    return closest_name
