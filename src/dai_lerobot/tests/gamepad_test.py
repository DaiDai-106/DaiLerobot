"""最简手柄事件监视：打印 event 类型、轴索引与值、按键编号与按下/松开。"""
import sys
import pygame


def main() -> None:
    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        print("未检测到手柄", file=sys.stderr)
        sys.exit(1)

    js = pygame.joystick.Joystick(0)
    js.init()
    print(
        f"手柄: {js.get_name()!r}  按钮数={js.get_numbuttons()}  轴数={js.get_numaxes()}"
    )
    pygame.display.set_mode((1, 1))
    pygame.display.set_caption("gamepad_test")

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type == pygame.JOYBUTTONDOWN:
                print(f"BUTTON DOWN  index={event.button}")
            elif event.type == pygame.JOYBUTTONUP:
                print(f"BUTTON UP    index={event.button}")
            elif event.type == pygame.JOYAXISMOTION:
                print(f"AXIS         index={event.axis}  value={event.value:+.4f}")
            elif event.type == pygame.JOYHATMOTION:
                print(f"HAT          index={event.hat}  value={event.value}")
        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
